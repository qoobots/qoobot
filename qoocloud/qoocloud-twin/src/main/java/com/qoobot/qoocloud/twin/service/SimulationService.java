package com.qoobot.qoocloud.twin.service;

import org.springframework.stereotype.Service;

import java.util.*;

/**
 * SimulationService — 数字孪生仿真服务
 * 在数字孪生中预演任务、评估风险
 */
@Service
public class SimulationService {

    /**
     * Start a simulation in the digital twin environment.
     */
    public Map<String, Object> startSimulation(String environmentId, String taskDescription,
                                                Map<String, Object> parameters) {
        String simulationId = "sim_" + UUID.randomUUID().toString().substring(0, 8);

        Map<String, Object> result = new HashMap<>();
        result.put("simulationId", simulationId);
        result.put("environmentId", environmentId);
        result.put("status", "running");
        result.put("task", taskDescription);
        result.put("estimatedDurationMs", 5000);
        return result;
    }

    /**
     * Get simulation result.
     */
    public Map<String, Object> getSimulationResult(String simulationId) {
        Map<String, Object> result = new HashMap<>();
        result.put("simulationId", simulationId);
        result.put("status", "completed");
        result.put("success", true);
        result.put("riskLevel", "low");
        result.put("predictedOutcome", "Task completed successfully");
        result.put("anomaliesDetected", List.of());
        return result;
    }

    /**
     * Predict potential anomalies based on current state.
     */
    public Map<String, Object> predictAnomalies(String deviceId, Map<String, Object> currentState) {
        Map<String, Object> prediction = new HashMap<>();
        prediction.put("deviceId", deviceId);

        List<Map<String, Object>> risks = new ArrayList<>();

        // Check battery level
        Object battery = currentState.get("batteryPercent");
        if (battery instanceof Number && ((Number) battery).doubleValue() < 20) {
            risks.add(Map.of(
                "type", "LOW_BATTERY",
                "severity", "WARNING",
                "probability", 0.85,
                "message", "Battery below 20%, risk of shutdown"
            ));
        }

        // Check temperature
        Object temp = currentState.get("temperatureC");
        if (temp instanceof Number && ((Number) temp).doubleValue() > 70) {
            risks.add(Map.of(
                "type", "OVERHEATING",
                "severity", "CRITICAL",
                "probability", 0.9,
                "message", "Temperature exceeds 70°C, risk of hardware damage"
            ));
        }

        prediction.put("risks", risks);
        prediction.put("overallRiskLevel", risks.isEmpty() ? "low" :
                risks.stream().anyMatch(r -> "CRITICAL".equals(r.get("severity"))) ? "high" : "medium");

        return prediction;
    }
}
