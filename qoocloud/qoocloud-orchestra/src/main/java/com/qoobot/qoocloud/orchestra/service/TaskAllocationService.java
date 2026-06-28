package com.qoobot.qoocloud.orchestra.service;

import org.springframework.stereotype.Service;

import java.util.*;

/**
 * TaskAllocationService — 任务分配服务
 * 基于能力/位置/负载的最优任务分发
 */
@Service
public class TaskAllocationService {

    /**
     * Allocate a task to the best robot.
     */
    public AllocationResult allocateTask(String taskId, String taskType,
                                          Map<String, Object> requirements,
                                          List<RobotCapability> availableRobots) {
        if (availableRobots.isEmpty()) {
            return new AllocationResult(taskId, null, "no_robot_available", 0.0);
        }

        // Score each robot based on capability match, load, and distance
        RobotCapability best = null;
        double bestScore = -1;

        for (RobotCapability robot : availableRobots) {
            double score = scoreRobot(robot, taskType, requirements);
            if (score > bestScore) {
                bestScore = score;
                best = robot;
            }
        }

        if (best != null && bestScore > 0.5) {
            return new AllocationResult(taskId, best.deviceId, "allocated", bestScore);
        }

        return new AllocationResult(taskId, null, "no_suitable_robot", bestScore);
    }

    private double scoreRobot(RobotCapability robot, String taskType,
                               Map<String, Object> requirements) {
        double score = 0.0;

        // Capability match
        if (robot.capabilities.contains(taskType)) score += 0.4;

        // Load factor (lower is better)
        double loadFactor = 1.0 - Math.min(1.0, robot.currentLoad / 100.0);
        score += loadFactor * 0.3;

        // Battery level
        score += (robot.batteryPercent / 100.0) * 0.2;

        // Distance factor (closer is better)
        if (requirements.containsKey("targetLat") && requirements.containsKey("targetLng")) {
            double distance = calculateDistance(
                    robot.lastLatitude, robot.lastLongitude,
                    ((Number) requirements.get("targetLat")).doubleValue(),
                    ((Number) requirements.get("targetLng")).doubleValue());
            double distanceScore = Math.max(0, 1.0 - distance / 1000.0); // 1km range
            score += distanceScore * 0.1;
        }

        return score;
    }

    private double calculateDistance(double lat1, double lng1, double lat2, double lng2) {
        // Haversine formula (simplified)
        double dLat = Math.toRadians(lat2 - lat1);
        double dLng = Math.toRadians(lng2 - lng1);
        double a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2)) *
                Math.sin(dLng / 2) * Math.sin(dLng / 2);
        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return 6371 * c; // km
    }

    // Inner types

    public record AllocationResult(
            String taskId,
            String assignedRobot,
            String status,
            double score
    ) {}

    public static class RobotCapability {
        public String deviceId;
        public String deviceName;
        public Set<String> capabilities = new HashSet<>();
        public double currentLoad;
        public double batteryPercent;
        public double lastLatitude;
        public double lastLongitude;
    }
}
