package com.qoobot.qoocloud.orchestra.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * MonitorDashboardService — 多机器人监控面板
 * 实时状态总览、任务进度甘特图、集群健康度评分。
 *
 * 功能对标：AWS IoT Fleet Hub + Grafana Dashboard
 */
@Service
public class MonitorDashboardService {

    private static final Logger log = LoggerFactory.getLogger(MonitorDashboardService.class);

    // 任务记录
    private final Map<String, TaskRecord> tasks = new ConcurrentHashMap<>();

    // 机器人状态快照
    private final Map<String, RobotSnapshot> robotSnapshots = new ConcurrentHashMap<>();

    // 告警事件
    private final List<AlertEvent> alertEvents = Collections.synchronizedList(new ArrayList<>());

    private static final int MAX_ALERTS = 500;

    // ==================== 任务进度管理 ====================

    /**
     * 注册任务并追踪进度。
     */
    public Map<String, Object> registerTask(String taskId, String taskName, String assignedRobot,
                                             int totalSteps, int estimatedDurationMinutes) {
        TaskRecord task = new TaskRecord(
                taskId, taskName, assignedRobot, totalSteps, estimatedDurationMinutes
        );
        tasks.put(taskId, task);

        log.info("Task registered: {} → robot={}, steps={}", taskId, assignedRobot, totalSteps);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("taskId", taskId);
        result.put("taskName", taskName);
        result.put("assignedRobot", assignedRobot);
        result.put("totalSteps", totalSteps);
        result.put("status", "pending");
        return result;
    }

    /**
     * 更新任务进度。
     */
    public Map<String, Object> updateTaskProgress(String taskId, int completedSteps,
                                                    String status, String message) {
        TaskRecord task = tasks.get(taskId);
        if (task == null) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("taskId", taskId);
            result.put("found", false);
            return result;
        }

        task.completedSteps = completedSteps;
        task.status = status;
        task.lastUpdate = Instant.now();
        if (message != null) {
            task.lastMessage = message;
        }

        if ("completed".equals(status) || "failed".equals(status)) {
            task.completedAt = Instant.now();
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("taskId", taskId);
        result.put("progress", String.format("%d/%d", completedSteps, task.totalSteps));
        result.put("progressPercent", task.totalSteps > 0
                ? Math.round(100.0 * completedSteps / task.totalSteps) : 0);
        result.put("status", status);
        result.put("message", message);
        return result;
    }

    /**
     * 生成任务进度甘特图数据。
     * 返回适合前端甘特图组件渲染的数据结构。
     */
    public Map<String, Object> getGanttChart() {
        List<Map<String, Object>> ganttItems = new ArrayList<>();

        for (TaskRecord task : tasks.values()) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("taskId", task.taskId);
            item.put("taskName", task.taskName);
            item.put("robotId", task.assignedRobot);
            item.put("status", task.status);
            item.put("startTime", task.createdAt.toString());
            item.put("lastUpdate", task.lastUpdate.toString());

            // 甘特图进度条
            int progressPercent = task.totalSteps > 0
                    ? Math.round(100.0f * task.completedSteps / task.totalSteps) : 0;
            item.put("progressPercent", progressPercent);
            item.put("completedSteps", task.completedSteps);
            item.put("totalSteps", task.totalSteps);

            // 预估剩余时间
            if (task.completedSteps > 0 && !"completed".equals(task.status)) {
                Duration elapsed = Duration.between(task.createdAt, Instant.now());
                long elapsedMs = elapsed.toMillis();
                long estimatedTotalMs = elapsedMs * task.totalSteps / task.completedSteps;
                long remainingMs = estimatedTotalMs - elapsedMs;
                item.put("estimatedRemainingMinutes", Math.round(remainingMs / 60000.0));
            } else if ("completed".equals(task.status)) {
                item.put("estimatedRemainingMinutes", 0);
            }

            // 完成时间
            if (task.completedAt != null) {
                item.put("completedAt", task.completedAt.toString());
                item.put("durationMinutes",
                        Duration.between(task.createdAt, task.completedAt).toMinutes());
            }

            item.put("lastMessage", task.lastMessage);
            ganttItems.add(item);
        }

        // 按创建时间排序
        ganttItems.sort(Comparator.comparing(item -> (String) item.get("startTime")));

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("items", ganttItems);
        result.put("totalTasks", ganttItems.size());
        result.put("generatedAt", Instant.now().toString());
        return result;
    }

    /**
     * 按机器人分组任务进度。
     */
    public Map<String, Object> getTasksByRobot() {
        Map<String, List<Map<String, Object>>> grouped = new LinkedHashMap<>();

        for (TaskRecord task : tasks.values()) {
            grouped.computeIfAbsent(task.assignedRobot, k -> new ArrayList<>());

            Map<String, Object> item = new LinkedHashMap<>();
            item.put("taskId", task.taskId);
            item.put("taskName", task.taskName);
            item.put("status", task.status);
            item.put("progressPercent", task.totalSteps > 0
                    ? Math.round(100.0f * task.completedSteps / task.totalSteps) : 0);
            item.put("lastMessage", task.lastMessage);
            grouped.get(task.assignedRobot).add(item);
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("groups", grouped);
        result.put("totalRobots", grouped.size());
        return result;
    }

    // ==================== 实时状态总览 ====================

    /**
     * 更新机器人状态快照。
     */
    public void updateRobotSnapshot(String robotId, String status, double cpuUsage,
                                     double memoryUsage, double batteryLevel,
                                     String currentTask, double[] position) {
        RobotSnapshot snapshot = new RobotSnapshot(
                robotId, status, cpuUsage, memoryUsage, batteryLevel,
                currentTask, position, Instant.now()
        );
        robotSnapshots.put(robotId, snapshot);

        // 自动告警检测
        if (batteryLevel < 15) {
            raiseAlert("low_battery", robotId,
                    String.format("Battery critical: %.1f%%", batteryLevel), "warning");
        }
        if (cpuUsage > 90) {
            raiseAlert("high_cpu", robotId,
                    String.format("CPU overload: %.1f%%", cpuUsage), "warning");
        }
        if ("offline".equals(status) || "error".equals(status)) {
            raiseAlert("status_change", robotId,
                    String.format("Robot status changed to: %s", status), "error");
        }
    }

    /**
     * 获取集群实时状态总览。
     */
    public Map<String, Object> getClusterOverview() {
        Map<String, Object> overview = new LinkedHashMap<>();
        overview.put("timestamp", Instant.now().toString());

        // 机器人状态统计
        long online = robotSnapshots.values().stream()
                .filter(s -> "online".equals(s.status) || "busy".equals(s.status)).count();
        long idle = robotSnapshots.values().stream()
                .filter(s -> "idle".equals(s.status)).count();
        long offline = robotSnapshots.values().stream()
                .filter(s -> "offline".equals(s.status)).count();
        long error = robotSnapshots.values().stream()
                .filter(s -> "error".equals(s.status)).count();

        overview.put("totalRobots", robotSnapshots.size());
        overview.put("online", online);
        overview.put("idle", idle);
        overview.put("offline", offline);
        overview.put("error", error);

        // 聚合指标
        if (!robotSnapshots.isEmpty()) {
            double avgCpu = robotSnapshots.values().stream()
                    .mapToDouble(s -> s.cpuUsage).average().orElse(0);
            double avgMemory = robotSnapshots.values().stream()
                    .mapToDouble(s -> s.memoryUsage).average().orElse(0);
            double avgBattery = robotSnapshots.values().stream()
                    .mapToDouble(s -> s.batteryLevel).average().orElse(0);

            overview.put("avgCpuUsage", Math.round(avgCpu * 10.0) / 10.0);
            overview.put("avgMemoryUsage", Math.round(avgMemory * 10.0) / 10.0);
            overview.put("avgBatteryLevel", Math.round(avgBattery * 10.0) / 10.0);
        }

        // 集群健康度评分（0-100）
        double healthScore = computeClusterHealthScore();
        overview.put("healthScore", Math.round(healthScore));
        overview.put("healthStatus", healthScore >= 80 ? "healthy"
                : healthScore >= 50 ? "degraded" : "critical");

        // 活跃告警数
        long activeAlerts = alertEvents.stream()
                .filter(a -> a.resolvedAt == null).count();
        overview.put("activeAlerts", activeAlerts);

        // 进行中任务数
        long runningTasks = tasks.values().stream()
                .filter(t -> "running".equals(t.status) || "pending".equals(t.status)).count();
        overview.put("runningTasks", runningTasks);

        return overview;
    }

    /**
     * 获取所有机器人详细状态列表。
     */
    public List<Map<String, Object>> getRobotDetails() {
        return robotSnapshots.values().stream()
                .sorted(Comparator.comparing(s -> s.robotId))
                .map(s -> {
                    Map<String, Object> detail = new LinkedHashMap<>();
                    detail.put("robotId", s.robotId);
                    detail.put("status", s.status);
                    detail.put("cpuUsage", s.cpuUsage);
                    detail.put("memoryUsage", s.memoryUsage);
                    detail.put("batteryLevel", s.batteryLevel);
                    detail.put("currentTask", s.currentTask);
                    detail.put("position", Map.of(
                            "x", s.position[0], "y", s.position[1], "z", s.position[2]
                    ));
                    detail.put("lastHeartbeat", s.lastHeartbeat.toString());
                    detail.put("onlineDuration",
                            Duration.between(s.lastHeartbeat, Instant.now()).toMinutes() + " min ago");
                    return detail;
                })
                .collect(Collectors.toList());
    }

    // ==================== 告警管理 ====================

    /**
     * 触发告警。
     */
    public Map<String, Object> raiseAlert(String alertType, String robotId,
                                           String message, String severity) {
        AlertEvent alert = new AlertEvent(
                UUID.randomUUID().toString().substring(0, 8),
                alertType, robotId, message, severity
        );
        alertEvents.add(alert);

        // 限制告警数量
        while (alertEvents.size() > MAX_ALERTS) {
            alertEvents.remove(0);
        }

        log.warn("Alert raised: type={}, robot={}, severity={}, message={}",
                alertType, robotId, severity, message);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("alertId", alert.alertId);
        result.put("type", alertType);
        result.put("robotId", robotId);
        result.put("severity", severity);
        result.put("message", message);
        result.put("timestamp", alert.raisedAt.toString());
        return result;
    }

    /**
     * 获取活跃告警列表。
     */
    public List<Map<String, Object>> getActiveAlerts(String severityFilter, int limit) {
        return alertEvents.stream()
                .filter(a -> a.resolvedAt == null)
                .filter(a -> severityFilter == null || severityFilter.equals(a.severity))
                .sorted(Comparator.comparing(a -> a.raisedAt, Comparator.reverseOrder()))
                .limit(limit)
                .map(a -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("alertId", a.alertId);
                    m.put("type", a.alertType);
                    m.put("robotId", a.robotId);
                    m.put("severity", a.severity);
                    m.put("message", a.message);
                    m.put("raisedAt", a.raisedAt.toString());
                    return m;
                })
                .collect(Collectors.toList());
    }

    /**
     * 解决告警。
     */
    public Map<String, Object> resolveAlert(String alertId) {
        for (AlertEvent alert : alertEvents) {
            if (alert.alertId.equals(alertId) && alert.resolvedAt == null) {
                alert.resolvedAt = Instant.now();
                Map<String, Object> result = new LinkedHashMap<>();
                result.put("alertId", alertId);
                result.put("resolved", true);
                result.put("resolvedAt", alert.resolvedAt.toString());
                return result;
            }
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("alertId", alertId);
        result.put("resolved", false);
        result.put("reason", "alert not found or already resolved");
        return result;
    }

    // ==================== 辅助方法 ====================

    private double computeClusterHealthScore() {
        if (robotSnapshots.isEmpty()) return 0;

        double score = 100.0;

        // 离线/错误设备扣分
        long problemCount = robotSnapshots.values().stream()
                .filter(s -> "offline".equals(s.status) || "error".equals(s.status))
                .count();
        score -= problemCount * 20.0;

        // 平均资源压力扣分
        double avgCpu = robotSnapshots.values().stream()
                .mapToDouble(s -> s.cpuUsage).average().orElse(0);
        double avgMem = robotSnapshots.values().stream()
                .mapToDouble(s -> s.memoryUsage).average().orElse(0);
        if (avgCpu > 80) score -= (avgCpu - 80) * 0.5;
        if (avgMem > 80) score -= (avgMem - 80) * 0.5;

        // 活跃告警扣分
        long activeAlerts = alertEvents.stream()
                .filter(a -> a.resolvedAt == null).count();
        score -= activeAlerts * 2.0;

        return Math.max(0, Math.min(100, score));
    }

    // ==================== 内部类 ====================

    static class TaskRecord {
        final String taskId;
        final String taskName;
        final String assignedRobot;
        final int totalSteps;
        final int estimatedDurationMinutes;
        int completedSteps;
        String status;       // pending/running/completed/failed
        String lastMessage;
        final Instant createdAt;
        Instant lastUpdate;
        Instant completedAt;

        TaskRecord(String taskId, String taskName, String assignedRobot,
                   int totalSteps, int estimatedDurationMinutes) {
            this.taskId = taskId;
            this.taskName = taskName;
            this.assignedRobot = assignedRobot;
            this.totalSteps = totalSteps;
            this.estimatedDurationMinutes = estimatedDurationMinutes;
            this.completedSteps = 0;
            this.status = "pending";
            this.lastMessage = "";
            this.createdAt = Instant.now();
            this.lastUpdate = Instant.now();
        }
    }

    static class RobotSnapshot {
        final String robotId;
        final String status;
        final double cpuUsage;
        final double memoryUsage;
        final double batteryLevel;
        final String currentTask;
        final double[] position;
        final Instant lastHeartbeat;

        RobotSnapshot(String robotId, String status, double cpuUsage, double memoryUsage,
                      double batteryLevel, String currentTask, double[] position,
                      Instant lastHeartbeat) {
            this.robotId = robotId;
            this.status = status;
            this.cpuUsage = cpuUsage;
            this.memoryUsage = memoryUsage;
            this.batteryLevel = batteryLevel;
            this.currentTask = currentTask;
            this.position = position;
            this.lastHeartbeat = lastHeartbeat;
        }
    }

    static class AlertEvent {
        final String alertId;
        final String alertType;
        final String robotId;
        final String message;
        final String severity;   // info/warning/error/critical
        final Instant raisedAt;
        Instant resolvedAt;

        AlertEvent(String alertId, String alertType, String robotId,
                   String message, String severity) {
            this.alertId = alertId;
            this.alertType = alertType;
            this.robotId = robotId;
            this.message = message;
            this.severity = severity;
            this.raisedAt = Instant.now();
        }
    }
}
