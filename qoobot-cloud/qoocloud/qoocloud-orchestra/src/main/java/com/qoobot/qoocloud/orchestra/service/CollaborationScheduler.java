package com.qoobot.qoocloud.orchestra.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * CollaborationScheduler — 协作调度服务
 * 多机器人协同作业的时序调度与冲突解决
 */
@Service
public class CollaborationScheduler {

    private static final Logger log = LoggerFactory.getLogger(CollaborationScheduler.class);

    // 协作任务存储
    private final Map<String, CollaborationTask> tasks = new ConcurrentHashMap<>();
    // 调度时间线（每个机器人 → 已分配的时间槽）
    private final Map<String, List<TimeSlot>> robotSchedules = new ConcurrentHashMap<>();
    // 冲突记录
    private final List<ScheduleConflict> conflicts = Collections.synchronizedList(new ArrayList<>());

    /**
     * 创建协作任务。
     */
    public CollaborationTask createTask(String name, String description,
                                         List<TaskStep> steps, TaskPriority priority) {
        String taskId = "ctask_" + UUID.randomUUID().toString().substring(0, 8);

        CollaborationTask task = new CollaborationTask();
        task.taskId = taskId;
        task.name = name;
        task.description = description;
        task.steps = steps;
        task.priority = priority;
        task.status = TaskStatus.PENDING;
        task.createdAt = Instant.now();

        tasks.put(taskId, task);
        log.info("Collaboration task created: {} ({}) — {} steps", name, taskId, steps.size());
        return task;
    }

    /**
     * 调度任务：为每个步骤分配时间槽，检测并解决冲突。
     */
    public ScheduleResult scheduleTask(String taskId) {
        CollaborationTask task = tasks.get(taskId);
        if (task == null) {
            return ScheduleResult.error("Task not found: " + taskId);
        }

        List<ScheduleConflict> detectedConflicts = new ArrayList<>();
        Instant baseTime = Instant.now();

        for (int i = 0; i < task.steps.size(); i++) {
            TaskStep step = task.steps.get(i);
            Instant stepStart = baseTime.plusSeconds(step.offsetSeconds);
            TimeSlot slot = new TimeSlot(
                    stepStart,
                    stepStart.plusSeconds(step.durationSeconds),
                    step.robotId,
                    taskId,
                    step.stepId
            );

            // 检测冲突：检查该机器人是否已有重叠的时间槽
            List<TimeSlot> existingSlots = robotSchedules.getOrDefault(step.robotId, List.of());
            for (TimeSlot existing : existingSlots) {
                if (isOverlapping(slot, existing)) {
                    ScheduleConflict conflict = new ScheduleConflict();
                    conflict.taskA = taskId;
                    conflict.taskB = existing.taskId;
                    conflict.robotId = step.robotId;
                    conflict.slotA = slot;
                    conflict.slotB = existing;
                    conflict.conflictType = ConflictType.TIME_OVERLAP;
                    conflict.detectedAt = Instant.now();

                    detectedConflicts.add(conflict);
                    conflicts.add(conflict);
                }
            }

            // 分配时间槽
            robotSchedules.computeIfAbsent(step.robotId, k -> new ArrayList<>()).add(slot);
        }

        if (detectedConflicts.isEmpty()) {
            task.status = TaskStatus.SCHEDULED;
            task.scheduledAt = Instant.now();
            tasks.put(taskId, task);
            return new ScheduleResult(taskId, "scheduled", List.of());
        } else {
            // 尝试解决冲突
            List<ScheduleConflict> resolved = resolveConflicts(detectedConflicts);
            task.status = resolved.isEmpty() ? TaskStatus.SCHEDULED : TaskStatus.CONFLICT;
            task.scheduledAt = Instant.now();
            tasks.put(taskId, task);
            return new ScheduleResult(taskId, task.status.name().toLowerCase(), resolved);
        }
    }

    /**
     * 解决调度冲突。
     */
    private List<ScheduleConflict> resolveConflicts(List<ScheduleConflict> conflicts) {
        List<ScheduleConflict> unresolved = new ArrayList<>();

        for (ScheduleConflict conflict : conflicts) {
            // 策略1：基于优先级解决
            CollaborationTask taskA = tasks.get(conflict.taskA);
            CollaborationTask taskB = tasks.get(conflict.taskB);

            if (taskA != null && taskB != null) {
                if (taskA.priority.ordinal() > taskB.priority.ordinal()) {
                    // taskA 优先级更高，调整 taskB
                    shiftTask(taskB.taskId, conflict.slotA.endTime);
                    conflict.resolved = true;
                    conflict.resolution = "Shifted lower priority task " + taskB.taskId;
                } else if (taskB.priority.ordinal() > taskA.priority.ordinal()) {
                    shiftTask(taskA.taskId, conflict.slotB.endTime);
                    conflict.resolved = true;
                    conflict.resolution = "Shifted lower priority task " + taskA.taskId;
                } else {
                    // 同等优先级：基于创建时间
                    if (taskA.createdAt.isBefore(taskB.createdAt)) {
                        shiftTask(taskB.taskId, conflict.slotA.endTime);
                        conflict.resolved = true;
                        conflict.resolution = "Shifted later task " + taskB.taskId;
                    } else {
                        shiftTask(taskA.taskId, conflict.slotB.endTime);
                        conflict.resolved = true;
                        conflict.resolution = "Shifted later task " + taskA.taskId;
                    }
                }
            }

            if (!conflict.resolved) {
                unresolved.add(conflict);
            }
        }

        return unresolved;
    }

    /**
     * 平移任务的所有时间槽。
     */
    private void shiftTask(String taskId, Instant newStartTime) {
        CollaborationTask task = tasks.get(taskId);
        if (task == null) return;

        Instant originalStart = task.steps.get(0).offsetSeconds > 0 ?
                task.createdAt.plusSeconds(task.steps.get(0).offsetSeconds) : task.createdAt;
        long shiftSeconds = Duration.between(originalStart, newStartTime).getSeconds();

        for (List<TimeSlot> slots : robotSchedules.values()) {
            for (TimeSlot slot : slots) {
                if (slot.taskId.equals(taskId)) {
                    slot.startTime = slot.startTime.plusSeconds(shiftSeconds);
                    slot.endTime = slot.endTime.plusSeconds(shiftSeconds);
                }
            }
        }
    }

    /**
     * 检查两个时间槽是否重叠。
     */
    private boolean isOverlapping(TimeSlot a, TimeSlot b) {
        return a.startTime.isBefore(b.endTime) && b.startTime.isBefore(a.endTime);
    }

    /**
     * 获取机器人调度时间线。
     */
    public List<TimeSlot> getRobotSchedule(String robotId) {
        return robotSchedules.getOrDefault(robotId, List.of()).stream()
                .sorted(Comparator.comparing(TimeSlot::getStartTime))
                .toList();
    }

    /**
     * 获取所有协作任务。
     */
    public List<CollaborationTask> listTasks() {
        return new ArrayList<>(tasks.values());
    }

    /**
     * 获取未解决的冲突。
     */
    public List<ScheduleConflict> getUnresolvedConflicts() {
        return conflicts.stream()
                .filter(c -> !c.resolved)
                .toList();
    }

    /**
     * 获取协作任务状态。
     */
    public Optional<CollaborationTask> getTask(String taskId) {
        return Optional.ofNullable(tasks.get(taskId));
    }

    // --- Inner Types ---

    public enum TaskStatus {
        PENDING, SCHEDULED, IN_PROGRESS, COMPLETED, CONFLICT, FAILED
    }

    public enum TaskPriority {
        LOW, NORMAL, HIGH, CRITICAL
    }

    public enum ConflictType {
        TIME_OVERLAP, RESOURCE_CONTENTION, SPATIAL_INTERFERENCE
    }

    public static class CollaborationTask {
        public String taskId;
        public String name;
        public String description;
        public List<TaskStep> steps = new ArrayList<>();
        public TaskPriority priority = TaskPriority.NORMAL;
        public TaskStatus status = TaskStatus.PENDING;
        public Instant createdAt;
        public Instant scheduledAt;
    }

    public static class TaskStep {
        public String stepId;
        public String robotId;
        public String action;         // navigate_to, pick_object, place_object, wait, observe
        public long offsetSeconds;    // 相对于任务开始时间的偏移
        public long durationSeconds;  // 步骤持续时长
        public Map<String, Object> parameters = new HashMap<>();
    }

    public static class TimeSlot {
        public Instant startTime;
        public Instant endTime;
        public String robotId;
        public String taskId;
        public String stepId;

        public TimeSlot(Instant start, Instant end, String robotId, String taskId, String stepId) {
            this.startTime = start;
            this.endTime = end;
            this.robotId = robotId;
            this.taskId = taskId;
            this.stepId = stepId;
        }

        public Instant getStartTime() { return startTime; }
    }

    public static class ScheduleConflict {
        public String taskA;
        public String taskB;
        public String robotId;
        public TimeSlot slotA;
        public TimeSlot slotB;
        public ConflictType conflictType;
        public Instant detectedAt;
        public boolean resolved;
        public String resolution;
    }

    public record ScheduleResult(
            String taskId,
            String status,
            List<ScheduleConflict> conflicts
    ) {
        public static ScheduleResult error(String message) {
            return new ScheduleResult(null, "error", List.of());
        }
    }
}
