package com.qoobot.qoocloud.orchestra.controller;

import com.qoobot.qoocloud.orchestra.service.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST API for multi-robot orchestration: clusters, tasks, scheduling, resource optimization.
 */
@RestController
@RequestMapping("/api/v1/orchestra")
public class OrchestraController {

    private final ClusterService clusterService;
    private final TaskAllocationService taskAllocationService;
    private final CollaborationScheduler collaborationScheduler;
    private final ResourceOptimizer resourceOptimizer;
    private final ScenarioOrchestrator scenarioOrchestrator;

    public OrchestraController(ClusterService clusterService,
                                TaskAllocationService taskAllocationService,
                                CollaborationScheduler collaborationScheduler,
                                ResourceOptimizer resourceOptimizer,
                                ScenarioOrchestrator scenarioOrchestrator) {
        this.clusterService = clusterService;
        this.taskAllocationService = taskAllocationService;
        this.collaborationScheduler = collaborationScheduler;
        this.resourceOptimizer = resourceOptimizer;
        this.scenarioOrchestrator = scenarioOrchestrator;
    }

    // ================================================================
    // 集群管理
    // ================================================================

    @PostMapping("/clusters")
    public ResponseEntity<ClusterService.Cluster> createCluster(@RequestBody Map<String, Object> body) {
        String name = (String) body.get("name");
        String description = (String) body.getOrDefault("description", "").toString();
        String ownerId = (String) body.get("ownerId");
        return ResponseEntity.ok(clusterService.createCluster(name, description, ownerId));
    }

    @GetMapping("/clusters")
    public ResponseEntity<List<ClusterService.Cluster>> listClusters() {
        return ResponseEntity.ok(clusterService.listClusters());
    }

    @PostMapping("/clusters/{clusterId}/robots")
    public ResponseEntity<Void> registerRobot(
            @PathVariable String clusterId,
            @RequestBody Map<String, Object> body) {
        String deviceId = (String) body.get("deviceId");
        String role = (String) body.getOrDefault("role", "worker");
        clusterService.registerRobot(clusterId, deviceId, role);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/clusters/{clusterId}/topology")
    public ResponseEntity<Map<String, Object>> getTopology(@PathVariable String clusterId) {
        return ResponseEntity.ok(clusterService.getTopology(clusterId));
    }

    // ================================================================
    // 任务分配
    // ================================================================

    @PostMapping("/tasks/allocate")
    public ResponseEntity<TaskAllocationService.AllocationResult> allocateTask(
            @RequestBody Map<String, Object> body) {
        String taskId = (String) body.get("taskId");
        String taskType = (String) body.get("taskType");
        @SuppressWarnings("unchecked")
        Map<String, Object> requirements = (Map<String, Object>) body.getOrDefault("requirements", Map.of());
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> robotsRaw = (List<Map<String, Object>>) body.get("availableRobots");
        List<TaskAllocationService.RobotCapability> robots = robotsRaw.stream()
                .map(r -> {
                    TaskAllocationService.RobotCapability cap = new TaskAllocationService.RobotCapability();
                    cap.deviceId = (String) r.get("deviceId");
                    cap.deviceName = (String) r.get("deviceName");
                    cap.currentLoad = ((Number) r.getOrDefault("currentLoad", 0)).doubleValue();
                    cap.batteryPercent = ((Number) r.getOrDefault("batteryPercent", 100)).doubleValue();
                    cap.lastLatitude = ((Number) r.getOrDefault("lat", 0)).doubleValue();
                    cap.lastLongitude = ((Number) r.getOrDefault("lng", 0)).doubleValue();
                    @SuppressWarnings("unchecked")
                    List<String> caps = (List<String>) r.getOrDefault("capabilities", List.of());
                    cap.capabilities.addAll(caps);
                    return cap;
                }).toList();
        return ResponseEntity.ok(taskAllocationService.allocateTask(taskId, taskType, requirements, robots));
    }

    // ================================================================
    // 协作调度
    // ================================================================

    @PostMapping("/scheduler/tasks")
    public ResponseEntity<CollaborationScheduler.CollaborationTask> createCollaborationTask(
            @RequestBody Map<String, Object> body) {
        String name = (String) body.get("name");
        String description = (String) body.getOrDefault("description", "").toString();
        CollaborationScheduler.TaskPriority priority = CollaborationScheduler.TaskPriority.valueOf(
                (String) body.getOrDefault("priority", "NORMAL"));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> stepsRaw = (List<Map<String, Object>>) body.get("steps");
        List<CollaborationScheduler.TaskStep> steps = stepsRaw.stream()
                .map(s -> {
                    CollaborationScheduler.TaskStep step = new CollaborationScheduler.TaskStep();
                    step.stepId = (String) s.get("stepId");
                    step.robotId = (String) s.get("robotId");
                    step.action = (String) s.get("action");
                    step.offsetSeconds = ((Number) s.getOrDefault("offsetSeconds", 0)).longValue();
                    step.durationSeconds = ((Number) s.getOrDefault("durationSeconds", 10)).longValue();
                    return step;
                }).toList();
        return ResponseEntity.ok(collaborationScheduler.createTask(name, description, steps, priority));
    }

    @PostMapping("/scheduler/tasks/{taskId}/schedule")
    public ResponseEntity<CollaborationScheduler.ScheduleResult> scheduleTask(
            @PathVariable String taskId) {
        return ResponseEntity.ok(collaborationScheduler.scheduleTask(taskId));
    }

    @GetMapping("/scheduler/tasks")
    public ResponseEntity<List<CollaborationScheduler.CollaborationTask>> listTasks() {
        return ResponseEntity.ok(collaborationScheduler.listTasks());
    }

    @GetMapping("/scheduler/robots/{robotId}/schedule")
    public ResponseEntity<List<CollaborationScheduler.TimeSlot>> getRobotSchedule(
            @PathVariable String robotId) {
        return ResponseEntity.ok(collaborationScheduler.getRobotSchedule(robotId));
    }

    @GetMapping("/scheduler/conflicts")
    public ResponseEntity<List<CollaborationScheduler.ScheduleConflict>> getConflicts() {
        return ResponseEntity.ok(collaborationScheduler.getUnresolvedConflicts());
    }

    // ================================================================
    // 资源优化
    // ================================================================

    @PostMapping("/resources/charging-stations")
    public ResponseEntity<ResourceOptimizer.ChargingStation> registerChargingStation(
            @RequestBody Map<String, Object> body) {
        String stationId = (String) body.get("stationId");
        String location = (String) body.get("location");
        int capacity = ((Number) body.getOrDefault("capacity", 4)).intValue();
        double lat = ((Number) body.get("lat")).doubleValue();
        double lng = ((Number) body.get("lng")).doubleValue();
        return ResponseEntity.ok(resourceOptimizer.registerChargingStation(
                stationId, location, capacity, lat, lng));
    }

    @PostMapping("/resources/charging/request")
    public ResponseEntity<ResourceOptimizer.ChargingAssignment> requestCharging(
            @RequestBody Map<String, Object> body) {
        String robotId = (String) body.get("robotId");
        double batteryPercent = ((Number) body.get("batteryPercent")).doubleValue();
        double lat = ((Number) body.getOrDefault("lat", 0)).doubleValue();
        double lng = ((Number) body.getOrDefault("lng", 0)).doubleValue();
        return ResponseEntity.ok(resourceOptimizer.requestCharging(robotId, batteryPercent, lat, lng));
    }

    @PostMapping("/resources/charging/complete")
    public ResponseEntity<Void> completeCharging(@RequestBody Map<String, Object> body) {
        String stationId = (String) body.get("stationId");
        String robotId = (String) body.get("robotId");
        resourceOptimizer.completeCharging(stationId, robotId);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/resources/congestion")
    public ResponseEntity<List<ResourceOptimizer.CongestionHotspot>> getCongestion() {
        return ResponseEntity.ok(resourceOptimizer.getActiveHotspots());
    }

    @PostMapping("/resources/allocate")
    public ResponseEntity<ResourceOptimizer.ResourceAllocation> optimizeAllocation(
            @RequestBody Map<String, Object> body) {
        String taskId = (String) body.get("taskId");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> requestsRaw = (List<Map<String, Object>>) body.get("requests");
        List<ResourceOptimizer.ResourceRequest> requests = requestsRaw.stream()
                .map(r -> new ResourceOptimizer.ResourceRequest(
                        (String) r.get("resourceType"),
                        ((Number) r.get("amount")).doubleValue(),
                        ((Number) r.getOrDefault("priority", 1)).intValue()))
                .toList();
        return ResponseEntity.ok(resourceOptimizer.optimizeAllocation(taskId, requests));
    }

    // ================================================================
    // 场景编排
    // ================================================================

    @GetMapping("/scenarios/templates")
    public ResponseEntity<List<ScenarioOrchestrator.ScenarioTemplate>> listTemplates(
            @RequestParam(required = false) String category) {
        return ResponseEntity.ok(scenarioOrchestrator.listTemplates(category));
    }

    @PostMapping("/scenarios/launch")
    public ResponseEntity<ScenarioOrchestrator.ScenarioInstance> launchScenario(
            @RequestBody Map<String, Object> body) {
        String templateId = (String) body.get("templateId");
        @SuppressWarnings("unchecked")
        List<String> robotIds = (List<String>) body.get("robotIds");
        @SuppressWarnings("unchecked")
        Map<String, Object> parameters = (Map<String, Object>) body.getOrDefault("parameters", Map.of());
        return ResponseEntity.ok(scenarioOrchestrator.launchScenario(templateId, robotIds, parameters));
    }

    @GetMapping("/scenarios/instances")
    public ResponseEntity<List<ScenarioOrchestrator.ScenarioInstance>> listInstances() {
        return ResponseEntity.ok(scenarioOrchestrator.listInstances());
    }

    @GetMapping("/scenarios/instances/{instanceId}")
    public ResponseEntity<ScenarioOrchestrator.ScenarioInstance> getInstance(
            @PathVariable String instanceId) {
        return scenarioOrchestrator.getInstance(instanceId)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/scenarios/instances/{instanceId}/progress")
    public ResponseEntity<ScenarioOrchestrator.ScenarioProgress> getProgress(
            @PathVariable String instanceId) {
        return ResponseEntity.ok(scenarioOrchestrator.getProgress(instanceId));
    }

    @PostMapping("/scenarios/instances/{instanceId}/steps")
    public ResponseEntity<Void> updateStepStatus(
            @PathVariable String instanceId,
            @RequestBody Map<String, Object> body) {
        String stepId = (String) body.get("stepId");
        ScenarioOrchestrator.StepStatus status = ScenarioOrchestrator.StepStatus.valueOf(
                (String) body.get("status"));
        String result = (String) body.getOrDefault("result", "");
        scenarioOrchestrator.updateStepStatus(instanceId, stepId, status, result);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/scenarios/instances/{instanceId}/control")
    public ResponseEntity<Void> controlScenario(
            @PathVariable String instanceId,
            @RequestBody Map<String, String> body) {
        scenarioOrchestrator.controlScenario(instanceId, body.get("command"));
        return ResponseEntity.ok().build();
    }
}
