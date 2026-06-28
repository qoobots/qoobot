package com.qoobot.qoocloud.orchestra.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * ScenarioOrchestrator — 场景编排服务
 * 定义多机器人协作场景（如仓库协同分拣、家庭多区域清洁）
 */
@Service
public class ScenarioOrchestrator {

    private static final Logger log = LoggerFactory.getLogger(ScenarioOrchestrator.class);

    // 场景模板库
    private final Map<String, ScenarioTemplate> templates = new ConcurrentHashMap<>();
    // 运行中的场景实例
    private final Map<String, ScenarioInstance> instances = new ConcurrentHashMap<>();

    public ScenarioOrchestrator() {
        // 预置场景模板
        initializePresetTemplates();
    }

    /**
     * 初始化预置场景模板。
     */
    private void initializePresetTemplates() {
        // 仓库协同分拣
        ScenarioTemplate warehousePicking = new ScenarioTemplate();
        warehousePicking.templateId = "scenario_warehouse_picking";
        warehousePicking.name = "仓库协同分拣";
        warehousePicking.description = "多机器人协同完成仓库订单分拣任务";
        warehousePicking.category = "warehouse";
        warehousePicking.minRobots = 2;
        warehousePicking.maxRobots = 10;
        warehousePicking.steps = List.of(
                createStep("order_receive", "接收订单", "dispatcher", 0, 5),
                createStep("zone_assignment", "区域分配", "dispatcher", 5, 3),
                createStep("pick_items", "分拣物品", "picker", 8, 30),
                createStep("transport_to_station", "运送到打包站", "transporter", 38, 15),
                createStep("quality_check", "质量检查", "inspector", 53, 10),
                createStep("package_handoff", "包裹交接", "transporter", 63, 5)
        );
        templates.put(warehousePicking.templateId, warehousePicking);

        // 家庭多区域清洁
        ScenarioTemplate homeCleaning = new ScenarioTemplate();
        homeCleaning.templateId = "scenario_home_cleaning";
        homeCleaning.name = "家庭多区域清洁";
        homeCleaning.description = "多机器人分区协作完成家庭清洁任务";
        homeCleaning.category = "home";
        homeCleaning.minRobots = 2;
        homeCleaning.maxRobots = 5;
        homeCleaning.steps = List.of(
                createStep("area_division", "区域划分", "coordinator", 0, 3),
                createStep("vacuum_living_room", "吸尘客厅", "cleaner", 3, 20),
                createStep("mop_kitchen", "拖地厨房", "cleaner", 3, 15),
                createStep("clean_bathroom", "清洁卫生间", "cleaner", 3, 12),
                createStep("dust_collection", "集尘汇总", "cleaner", 23, 5),
                createStep("completion_report", "完成报告", "coordinator", 28, 2)
        );
        templates.put(homeCleaning.templateId, homeCleaning);

        // 医院药品配送
        ScenarioTemplate hospitalDelivery = new ScenarioTemplate();
        hospitalDelivery.templateId = "scenario_hospital_delivery";
        hospitalDelivery.name = "医院药品配送";
        hospitalDelivery.description = "多机器人协同完成医院内药品和样本配送";
        hospitalDelivery.category = "healthcare";
        hospitalDelivery.minRobots = 2;
        hospitalDelivery.maxRobots = 8;
        hospitalDelivery.steps = List.of(
                createStep("order_from_pharmacy", "药房取药", "delivery_bot", 0, 10),
                createStep("route_planning", "路径规划", "dispatcher", 10, 3),
                createStep("deliver_to_ward", "配送到病房", "delivery_bot", 13, 15),
                createStep("nurse_confirmation", "护士确认", "delivery_bot", 28, 3),
                createStep("return_to_pharmacy", "返回药房", "delivery_bot", 31, 10)
        );
        templates.put(hospitalDelivery.templateId, hospitalDelivery);
    }

    /**
     * 创建自定义场景模板。
     */
    public ScenarioTemplate createTemplate(String name, String description, String category,
                                            int minRobots, int maxRobots,
                                            List<ScenarioStep> steps) {
        String templateId = "scenario_" + UUID.randomUUID().toString().substring(0, 8);

        ScenarioTemplate template = new ScenarioTemplate();
        template.templateId = templateId;
        template.name = name;
        template.description = description;
        template.category = category;
        template.minRobots = minRobots;
        template.maxRobots = maxRobots;
        template.steps = steps;
        template.createdAt = Instant.now();

        templates.put(templateId, template);
        log.info("Scenario template created: {} ({})", name, templateId);
        return template;
    }

    /**
     * 启动场景实例。
     */
    public ScenarioInstance launchScenario(String templateId, List<String> robotIds,
                                            Map<String, Object> parameters) {
        ScenarioTemplate template = templates.get(templateId);
        if (template == null) {
            throw new RuntimeException("Scenario template not found: " + templateId);
        }

        if (robotIds.size() < template.minRobots || robotIds.size() > template.maxRobots) {
            throw new RuntimeException(String.format(
                    "Robot count %d out of range [%d, %d] for scenario %s",
                    robotIds.size(), template.minRobots, template.maxRobots, template.name));
        }

        String instanceId = "sinst_" + UUID.randomUUID().toString().substring(0, 8);

        ScenarioInstance instance = new ScenarioInstance();
        instance.instanceId = instanceId;
        instance.templateId = templateId;
        instance.robotIds = robotIds;
        instance.parameters = parameters != null ? parameters : Map.of();
        instance.status = ScenarioStatus.INITIALIZING;
        instance.startedAt = Instant.now();

        // 分配步骤到机器人
        instance.stepAssignments = assignSteps(template.steps, robotIds);
        instance.totalSteps = template.steps.size();

        instances.put(instanceId, instance);
        log.info("Scenario launched: {} (template: {}) — {} robots",
                instanceId, template.name, robotIds.size());
        return instance;
    }

    /**
     * 更新场景步骤状态。
     */
    public void updateStepStatus(String instanceId, String stepId, StepStatus status,
                                  String result) {
        ScenarioInstance instance = instances.get(instanceId);
        if (instance == null) return;

        for (StepAssignment assignment : instance.stepAssignments) {
            if (assignment.stepId.equals(stepId)) {
                assignment.status = status;
                assignment.result = result;
                if (status == StepStatus.COMPLETED || status == StepStatus.FAILED) {
                    assignment.completedAt = Instant.now();
                    instance.completedSteps++;
                }
                break;
            }
        }

        // 检查场景是否全部完成
        if (instance.completedSteps >= instance.totalSteps) {
            boolean allSuccess = instance.stepAssignments.stream()
                    .allMatch(a -> a.status == StepStatus.COMPLETED);
            instance.status = allSuccess ? ScenarioStatus.COMPLETED : ScenarioStatus.PARTIALLY_COMPLETED;
            instance.completedAt = Instant.now();
            log.info("Scenario completed: {} — status: {}", instanceId, instance.status);
        }
    }

    /**
     * 暂停/恢复/停止场景。
     */
    public void controlScenario(String instanceId, String command) {
        ScenarioInstance instance = instances.get(instanceId);
        if (instance == null) return;

        switch (command.toLowerCase()) {
            case "pause" -> instance.status = ScenarioStatus.PAUSED;
            case "resume" -> instance.status = ScenarioStatus.RUNNING;
            case "stop" -> {
                instance.status = ScenarioStatus.STOPPED;
                instance.completedAt = Instant.now();
            }
            default -> log.warn("Unknown scenario command: {}", command);
        }
    }

    /**
     * 获取场景实例状态。
     */
    public Optional<ScenarioInstance> getInstance(String instanceId) {
        return Optional.ofNullable(instances.get(instanceId));
    }

    /**
     * 列出所有场景模板。
     */
    public List<ScenarioTemplate> listTemplates(String category) {
        return templates.values().stream()
                .filter(t -> category == null || t.category.equals(category))
                .toList();
    }

    /**
     * 列出运行中的场景实例。
     */
    public List<ScenarioInstance> listInstances() {
        return new ArrayList<>(instances.values());
    }

    /**
     * 获取场景进度。
     */
    public ScenarioProgress getProgress(String instanceId) {
        ScenarioInstance instance = instances.get(instanceId);
        if (instance == null) {
            return new ScenarioProgress(instanceId, 0, 0, "not_found");
        }

        return new ScenarioProgress(
                instanceId,
                instance.completedSteps,
                instance.totalSteps,
                instance.status.name().toLowerCase()
        );
    }

    /**
     * 分配步骤到机器人。
     */
    private List<StepAssignment> assignSteps(List<ScenarioStep> steps, List<String> robotIds) {
        List<StepAssignment> assignments = new ArrayList<>();
        int robotIndex = 0;

        for (ScenarioStep step : steps) {
            StepAssignment assignment = new StepAssignment();
            assignment.stepId = step.stepId;
            assignment.stepName = step.stepName;
            assignment.role = step.role;
            assignment.assignedRobot = robotIds.get(robotIndex % robotIds.size());
            assignment.status = StepStatus.PENDING;
            assignments.add(assignment);
            robotIndex++;
        }

        return assignments;
    }

    private ScenarioStep createStep(String stepId, String name, String role,
                                     int offsetSeconds, int durationSeconds) {
        ScenarioStep step = new ScenarioStep();
        step.stepId = stepId;
        step.stepName = name;
        step.role = role;
        step.offsetSeconds = offsetSeconds;
        step.durationSeconds = durationSeconds;
        return step;
    }

    // --- Inner Types ---

    public enum ScenarioStatus {
        INITIALIZING, RUNNING, PAUSED, COMPLETED, PARTIALLY_COMPLETED, STOPPED, FAILED
    }

    public enum StepStatus {
        PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED
    }

    public static class ScenarioTemplate {
        public String templateId;
        public String name;
        public String description;
        public String category;
        public int minRobots;
        public int maxRobots;
        public List<ScenarioStep> steps = new ArrayList<>();
        public Instant createdAt;
    }

    public static class ScenarioStep {
        public String stepId;
        public String stepName;
        public String role;         // 角色名称
        public int offsetSeconds;   // 相对偏移
        public int durationSeconds; // 预计时长
    }

    public static class ScenarioInstance {
        public String instanceId;
        public String templateId;
        public List<String> robotIds = new ArrayList<>();
        public Map<String, Object> parameters = new HashMap<>();
        public ScenarioStatus status;
        public List<StepAssignment> stepAssignments = new ArrayList<>();
        public int totalSteps;
        public int completedSteps;
        public Instant startedAt;
        public Instant completedAt;
    }

    public static class StepAssignment {
        public String stepId;
        public String stepName;
        public String role;
        public String assignedRobot;
        public StepStatus status;
        public String result;
        public Instant completedAt;
    }

    public record ScenarioProgress(
            String instanceId,
            int completedSteps,
            int totalSteps,
            String status
    ) {}
}
