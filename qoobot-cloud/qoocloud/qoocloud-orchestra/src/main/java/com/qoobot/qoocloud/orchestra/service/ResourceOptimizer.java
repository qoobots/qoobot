package com.qoobot.qoocloud.orchestra.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * ResourceOptimizer — 资源优化服务
 * 多机器人全局路径规划避免拥堵、充电调度、全局资源最优分配
 */
@Service
public class ResourceOptimizer {

    private static final Logger log = LoggerFactory.getLogger(ResourceOptimizer.class);

    // 拥堵热点
    private final Map<String, CongestionHotspot> congestionHotspots = new ConcurrentHashMap<>();
    // 充电队列（每个充电站 → 等待队列）
    private final Map<String, Deque<String>> chargingQueues = new ConcurrentHashMap<>();
    // 全局资源分配
    private final Map<String, ResourceAllocation> allocations = new ConcurrentHashMap<>();
    // 充电站注册
    private final Map<String, ChargingStation> chargingStations = new ConcurrentHashMap<>();

    /**
     * 注册充电站。
     */
    public ChargingStation registerChargingStation(String stationId, String location,
                                                     int capacity, double lat, double lng) {
        ChargingStation station = new ChargingStation();
        station.stationId = stationId;
        station.location = location;
        station.capacity = capacity;
        station.availableSlots = capacity;
        station.latitude = lat;
        station.longitude = lng;
        station.status = "active";

        chargingStations.put(stationId, station);
        chargingQueues.put(stationId, new ArrayDeque<>());
        log.info("Charging station registered: {} ({}) — {} slots", location, stationId, capacity);
        return station;
    }

    /**
     * 请求充电（加入队列或直接分配）。
     */
    public ChargingAssignment requestCharging(String robotId, double batteryPercent,
                                               double robotLat, double robotLng) {
        // 找到最近的可用充电站
        ChargingStation bestStation = null;
        double bestDistance = Double.MAX_VALUE;

        for (ChargingStation station : chargingStations.values()) {
            if (station.availableSlots > 0) {
                double distance = haversineDistance(robotLat, robotLng,
                        station.latitude, station.longitude);
                if (distance < bestDistance) {
                    bestDistance = distance;
                    bestStation = station;
                }
            }
        }

        if (bestStation != null) {
            bestStation.availableSlots--;
            bestStation.currentlyCharging.add(robotId);

            ChargingAssignment assignment = new ChargingAssignment();
            assignment.robotId = robotId;
            assignment.stationId = bestStation.stationId;
            assignment.assigned = true;
            assignment.distanceKm = bestDistance;
            assignment.position = 0; // 立即充电
            assignment.estimatedWaitMinutes = 0;

            log.info("Charging assigned: robot {} → station {} ({}km)",
                    robotId, bestStation.location, String.format("%.2f", bestDistance));
            return assignment;
        }

        // 所有充电站已满，加入最近的充电站队列
        ChargingStation queuedStation = findNearestStation(robotLat, robotLng);
        if (queuedStation != null) {
            Deque<String> queue = chargingQueues.get(queuedStation.stationId);
            if (queue != null) {
                queue.addLast(robotId);
                ChargingAssignment assignment = new ChargingAssignment();
                assignment.robotId = robotId;
                assignment.stationId = queuedStation.stationId;
                assignment.assigned = false;
                assignment.distanceKm = haversineDistance(robotLat, robotLng,
                        queuedStation.latitude, queuedStation.longitude);
                assignment.position = queue.size();
                assignment.estimatedWaitMinutes = queue.size() * 30; // 估算每次充电 30 分钟

                log.info("Charging queued: robot {} → station {} (position {})",
                        robotId, queuedStation.location, queue.size());
                return assignment;
            }
        }

        return ChargingAssignment.unavailable();
    }

    /**
     * 完成充电，释放充电槽。
     */
    public void completeCharging(String stationId, String robotId) {
        ChargingStation station = chargingStations.get(stationId);
        if (station != null) {
            station.currentlyCharging.remove(robotId);
            station.availableSlots++;

            // 从等待队列中取出下一个
            Deque<String> queue = chargingQueues.get(stationId);
            if (queue != null && !queue.isEmpty()) {
                String nextRobot = queue.pollFirst();
                station.availableSlots--;
                station.currentlyCharging.add(nextRobot);
                log.info("Charging slot assigned to queued robot: {} → {}", nextRobot, stationId);
            }
        }
    }

    /**
     * 检测并报告拥堵热点。
     */
    public CongestionHotspot detectCongestion(String areaId, double centerLat, double centerLng,
                                               int robotCount, double densityThreshold) {
        double density = robotCount / (Math.PI * 25); // 假设 5m 半径区域

        if (density > densityThreshold) {
            CongestionHotspot hotspot = new CongestionHotspot();
            hotspot.hotspotId = "cong_" + UUID.randomUUID().toString().substring(0, 8);
            hotspot.areaId = areaId;
            hotspot.centerLat = centerLat;
            hotspot.centerLng = centerLng;
            hotspot.robotCount = robotCount;
            hotspot.density = density;
            hotspot.severity = density > 1.0 ? "CRITICAL" : density > 0.5 ? "WARNING" : "INFO";
            hotspot.detectedAt = Instant.now();

            congestionHotspots.put(hotspot.hotspotId, hotspot);
            log.warn("Congestion detected: {} — {} robots, density {:.2f}",
                    areaId, robotCount, density);
            return hotspot;
        }

        return null;
    }

    /**
     * 获取拥堵规避建议。
     */
    public List<RerouteSuggestion> getRerouteSuggestions(double robotLat, double robotLng) {
        List<RerouteSuggestion> suggestions = new ArrayList<>();

        for (CongestionHotspot hotspot : congestionHotspots.values()) {
            double distance = haversineDistance(robotLat, robotLng,
                    hotspot.centerLat, hotspot.centerLng);
            if (distance < 50) { // 50米内的拥堵热点
                RerouteSuggestion suggestion = new RerouteSuggestion();
                suggestion.hotspotId = hotspot.hotspotId;
                suggestion.areaId = hotspot.areaId;
                suggestion.distanceMeters = distance * 1000;
                suggestion.severity = hotspot.severity;
                suggestion.recommendation = distance < 10 ?
                        "Immediate reroute recommended" :
                        "Consider alternative path";
                suggestions.add(suggestion);
            }
        }

        return suggestions;
    }

    /**
     * 全局资源优化分配。
     */
    public ResourceAllocation optimizeAllocation(String taskId, List<ResourceRequest> requests) {
        String allocationId = "alloc_" + UUID.randomUUID().toString().substring(0, 8);

        ResourceAllocation allocation = new ResourceAllocation();
        allocation.allocationId = allocationId;
        allocation.taskId = taskId;
        allocation.createdAt = Instant.now();

        // 贪心分配算法：按优先级排序请求，优先分配稀缺资源
        List<ResourceRequest> sorted = new ArrayList<>(requests);
        sorted.sort(Comparator.comparing(ResourceRequest::priority).reversed());

        List<ResourceAssignment> assignments = new ArrayList<>();
        double totalCost = 0;

        for (ResourceRequest request : sorted) {
            ResourceAssignment assignment = assignResource(request);
            if (assignment != null) {
                assignments.add(assignment);
                totalCost += assignment.estimatedCost;
            }
        }

        allocation.assignments = assignments;
        allocation.totalCost = totalCost;
        allocation.status = assignments.size() == requests.size() ? "fully_allocated" : "partially_allocated";

        allocations.put(allocationId, allocation);
        return allocation;
    }

    /**
     * 分配单个资源。
     */
    private ResourceAssignment assignResource(ResourceRequest request) {
        ResourceAssignment assignment = new ResourceAssignment();
        assignment.resourceType = request.resourceType;
        assignment.requestedAmount = request.amount;
        assignment.allocatedAmount = Math.min(request.amount, getAvailableCapacity(request.resourceType));
        assignment.estimatedCost = assignment.allocatedAmount * getUnitCost(request.resourceType);
        return assignment;
    }

    private double getAvailableCapacity(String resourceType) {
        return switch (resourceType) {
            case "gpu_memory_gb" -> 80;
            case "cpu_cores" -> 64;
            case "bandwidth_mbps" -> 1000;
            case "storage_gb" -> 500;
            default -> 100;
        };
    }

    private double getUnitCost(String resourceType) {
        return switch (resourceType) {
            case "gpu_memory_gb" -> 0.05;
            case "cpu_cores" -> 0.01;
            case "bandwidth_mbps" -> 0.001;
            case "storage_gb" -> 0.02;
            default -> 0.01;
        };
    }

    /**
     * 获取充电站列表。
     */
    public List<ChargingStation> getChargingStations() {
        return new ArrayList<>(chargingStations.values());
    }

    /**
     * 获取活跃拥堵热点。
     */
    public List<CongestionHotspot> getActiveHotspots() {
        return congestionHotspots.values().stream()
                .filter(h -> h.detectedAt.isAfter(Instant.now().minusSeconds(300)))
                .toList();
    }

    private ChargingStation findNearestStation(double lat, double lng) {
        ChargingStation nearest = null;
        double minDist = Double.MAX_VALUE;
        for (ChargingStation station : chargingStations.values()) {
            double dist = haversineDistance(lat, lng, station.latitude, station.longitude);
            if (dist < minDist) {
                minDist = dist;
                nearest = station;
            }
        }
        return nearest;
    }

    private double haversineDistance(double lat1, double lng1, double lat2, double lng2) {
        double dLat = Math.toRadians(lat2 - lat1);
        double dLng = Math.toRadians(lng2 - lng1);
        double a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2)) *
                Math.sin(dLng / 2) * Math.sin(dLng / 2);
        return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }

    // --- Inner Types ---

    public static class ChargingStation {
        public String stationId;
        public String location;
        public int capacity;
        public int availableSlots;
        public double latitude;
        public double longitude;
        public String status;
        public List<String> currentlyCharging = new ArrayList<>();
    }

    public static class ChargingAssignment {
        public String robotId;
        public String stationId;
        public boolean assigned;
        public double distanceKm;
        public int position;
        public int estimatedWaitMinutes;

        public static ChargingAssignment unavailable() {
            ChargingAssignment a = new ChargingAssignment();
            a.assigned = false;
            a.position = -1;
            return a;
        }
    }

    public static class CongestionHotspot {
        public String hotspotId;
        public String areaId;
        public double centerLat;
        public double centerLng;
        public int robotCount;
        public double density;
        public String severity;
        public Instant detectedAt;
    }

    public static class RerouteSuggestion {
        public String hotspotId;
        public String areaId;
        public double distanceMeters;
        public String severity;
        public String recommendation;
    }

    public record ResourceRequest(
            String resourceType,
            double amount,
            int priority
    ) {}

    public static class ResourceAllocation {
        public String allocationId;
        public String taskId;
        public List<ResourceAssignment> assignments = new ArrayList<>();
        public double totalCost;
        public String status;
        public Instant createdAt;
    }

    public static class ResourceAssignment {
        public String resourceType;
        public double requestedAmount;
        public double allocatedAmount;
        public double estimatedCost;
    }
}
