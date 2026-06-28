package com.qoobot.qoocloud.device.service;

import com.qoobot.qoocloud.device.entity.Device;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedDeque;
import java.util.stream.Collectors;

/**
 * DeviceMapService — 设备地图服务
 * GIS 可视化设备分布、轨迹回放、地理围栏。
 *
 * 功能对标：AWS IoT Device Location + AWS Location Service
 */
@Service
public class DeviceMapService {

    private static final Logger log = LoggerFactory.getLogger(DeviceMapService.class);

    // 设备位置历史（deviceId → 轨迹点队列，保留最近 10000 个点）
    private final Map<String, ConcurrentLinkedDeque<TrajectoryPoint>> trajectories = new ConcurrentHashMap<>();

    // 地理围栏定义
    private final Map<String, GeoFence> geoFences = new ConcurrentHashMap<>();

    // 最大轨迹点保留数
    private static final int MAX_TRAJECTORY_POINTS = 10_000;

    /**
     * 记录设备位置，用于轨迹回放。
     */
    public void recordLocation(String deviceId, double latitude, double longitude,
                               double altitude, double heading, double speed,
                               double batteryLevel, String status) {
        TrajectoryPoint point = new TrajectoryPoint(
                deviceId, latitude, longitude, altitude, heading, speed,
                batteryLevel, status, Instant.now()
        );

        trajectories.computeIfAbsent(deviceId, k -> new ConcurrentLinkedDeque<>());
        ConcurrentLinkedDeque<TrajectoryPoint> deque = trajectories.get(deviceId);

        synchronized (deque) {
            deque.addLast(point);
            while (deque.size() > MAX_TRAJECTORY_POINTS) {
                deque.removeFirst();
            }
        }

        // 检查地理围栏
        checkGeoFences(deviceId, latitude, longitude);
    }

    /**
     * 获取设备分布热力图数据。
     * 返回所有设备当前位置的聚合视图。
     */
    public Map<String, Object> getDeviceDistribution() {
        Map<String, Object> result = new LinkedHashMap<>();
        List<Map<String, Object>> devices = new ArrayList<>();

        for (Map.Entry<String, ConcurrentLinkedDeque<TrajectoryPoint>> entry : trajectories.entrySet()) {
            String deviceId = entry.getKey();
            ConcurrentLinkedDeque<TrajectoryPoint> deque = entry.getValue();
            TrajectoryPoint latest = deque.peekLast();
            if (latest != null) {
                Map<String, Object> point = new LinkedHashMap<>();
                point.put("deviceId", deviceId);
                point.put("latitude", latest.latitude);
                point.put("longitude", latest.longitude);
                point.put("altitude", latest.altitude);
                point.put("heading", latest.heading);
                point.put("speed", latest.speed);
                point.put("batteryLevel", latest.batteryLevel);
                point.put("status", latest.status);
                point.put("timestamp", latest.timestamp.toString());
                devices.add(point);
            }
        }

        result.put("devices", devices);
        result.put("total", devices.size());
        result.put("updatedAt", Instant.now().toString());
        return result;
    }

    /**
     * 获取设备分布聚合（按区域分组统计）。
     * 用于热力图和区域统计图表。
     */
    public Map<String, Object> getDeviceDistributionByRegion(double gridSizeDegrees) {
        Map<String, List<Map<String, Object>>> regions = new LinkedHashMap<>();

        for (Map.Entry<String, ConcurrentLinkedDeque<TrajectoryPoint>> entry : trajectories.entrySet()) {
            String deviceId = entry.getKey();
            TrajectoryPoint latest = entry.getValue().peekLast();
            if (latest != null) {
                // 按网格聚合
                int gridLat = (int) Math.floor(latest.latitude / gridSizeDegrees);
                int gridLon = (int) Math.floor(latest.longitude / gridSizeDegrees);
                String regionKey = String.format("%d_%d", gridLat, gridLon);

                regions.computeIfAbsent(regionKey, k -> new ArrayList<>());
                Map<String, Object> deviceInfo = new LinkedHashMap<>();
                deviceInfo.put("deviceId", deviceId);
                deviceInfo.put("latitude", latest.latitude);
                deviceInfo.put("longitude", latest.longitude);
                deviceInfo.put("status", latest.status);
                deviceInfo.put("batteryLevel", latest.batteryLevel);
                regions.get(regionKey).add(deviceInfo);
            }
        }

        Map<String, Object> result = new LinkedHashMap<>();
        List<Map<String, Object>> regionList = new ArrayList<>();
        for (Map.Entry<String, List<Map<String, Object>>> region : regions.entrySet()) {
            Map<String, Object> regionData = new LinkedHashMap<>();
            regionData.put("regionKey", region.getKey());
            regionData.put("deviceCount", region.getValue().size());
            regionData.put("devices", region.getValue());

            // 计算区域中心
            double avgLat = region.getValue().stream()
                    .mapToDouble(d -> (Double) d.get("latitude")).average().orElse(0);
            double avgLon = region.getValue().stream()
                    .mapToDouble(d -> (Double) d.get("longitude")).average().orElse(0);
            regionData.put("centerLatitude", avgLat);
            regionData.put("centerLongitude", avgLon);
            regionList.add(regionData);
        }

        result.put("regions", regionList);
        result.put("gridSizeDegrees", gridSizeDegrees);
        result.put("totalRegions", regionList.size());
        return result;
    }

    /**
     * 设备轨迹回放：获取指定设备在时间范围内的轨迹。
     */
    public Map<String, Object> getTrajectoryReplay(String deviceId, Instant from, Instant to) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("deviceId", deviceId);

        ConcurrentLinkedDeque<TrajectoryPoint> deque = trajectories.get(deviceId);
        if (deque == null) {
            result.put("points", List.of());
            result.put("count", 0);
            return result;
        }

        List<TrajectoryPoint> filtered;
        synchronized (deque) {
            filtered = deque.stream()
                    .filter(p -> !p.timestamp.isBefore(from) && !p.timestamp.isAfter(to))
                    .collect(Collectors.toList());
        }

        List<Map<String, Object>> points = filtered.stream().map(p -> {
            Map<String, Object> point = new LinkedHashMap<>();
            point.put("latitude", p.latitude);
            point.put("longitude", p.longitude);
            point.put("altitude", p.altitude);
            point.put("heading", p.heading);
            point.put("speed", p.speed);
            point.put("batteryLevel", p.batteryLevel);
            point.put("status", p.status);
            point.put("timestamp", p.timestamp.toString());
            return point;
        }).collect(Collectors.toList());

        result.put("points", points);
        result.put("count", points.size());
        result.put("from", from.toString());
        result.put("to", to.toString());
        return result;
    }

    /**
     * 设备最后位置查询。
     */
    public Map<String, Object> getDeviceLastLocation(String deviceId) {
        ConcurrentLinkedDeque<TrajectoryPoint> deque = trajectories.get(deviceId);
        if (deque == null || deque.isEmpty()) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("deviceId", deviceId);
            result.put("found", false);
            return result;
        }

        TrajectoryPoint latest = deque.peekLast();
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("deviceId", deviceId);
        result.put("found", true);
        result.put("latitude", latest.latitude);
        result.put("longitude", latest.longitude);
        result.put("altitude", latest.altitude);
        result.put("heading", latest.heading);
        result.put("speed", latest.speed);
        result.put("batteryLevel", latest.batteryLevel);
        result.put("status", latest.status);
        result.put("timestamp", latest.timestamp.toString());
        return result;
    }

    // ==================== 地理围栏 ====================

    /**
     * 创建地理围栏。
     */
    public Map<String, Object> createGeoFence(String fenceId, String name,
                                               double centerLat, double centerLon,
                                               double radiusMeters, String alertType) {
        GeoFence fence = new GeoFence(fenceId, name, centerLat, centerLon, radiusMeters, alertType);
        geoFences.put(fenceId, fence);

        log.info("Geo-fence created: {} (radius={}m, type={})", name, radiusMeters, alertType);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("fenceId", fenceId);
        result.put("name", name);
        result.put("centerLatitude", centerLat);
        result.put("centerLongitude", centerLon);
        result.put("radiusMeters", radiusMeters);
        result.put("alertType", alertType);
        return result;
    }

    /**
     * 列出所有地理围栏。
     */
    public List<Map<String, Object>> listGeoFences() {
        return geoFences.values().stream().map(f -> {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("fenceId", f.fenceId);
            m.put("name", f.name);
            m.put("centerLatitude", f.centerLat);
            m.put("centerLongitude", f.centerLon);
            m.put("radiusMeters", f.radiusMeters);
            m.put("alertType", f.alertType);
            m.put("lastTriggered", f.lastTriggered != null ? f.lastTriggered.toString() : null);
            return m;
        }).collect(Collectors.toList());
    }

    /**
     * 删除地理围栏。
     */
    public boolean deleteGeoFence(String fenceId) {
        return geoFences.remove(fenceId) != null;
    }

    private void checkGeoFences(String deviceId, double lat, double lon) {
        for (GeoFence fence : geoFences.values()) {
            double distance = haversineDistance(fence.centerLat, fence.centerLon, lat, lon);
            if (distance > fence.radiusMeters) {
                // 设备在围栏外 → 触发告警（仅 enter/exit 类型）
                if ("exit".equals(fence.alertType)) {
                    fence.lastTriggered = Instant.now();
                    log.warn("Device {} exited geo-fence '{}' (distance={}m)", deviceId, fence.name, distance);
                }
            }
        }
    }

    /**
     * Haversine 公式计算两点间距离（米）。
     */
    private double haversineDistance(double lat1, double lon1, double lat2, double lon2) {
        final double R = 6_371_000; // 地球半径（米）
        double dLat = Math.toRadians(lat2 - lat1);
        double dLon = Math.toRadians(lon2 - lon1);
        double a = Math.sin(dLat / 2) * Math.sin(dLat / 2)
                + Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2))
                * Math.sin(dLon / 2) * Math.sin(dLon / 2);
        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    // ==================== 内部类 ====================

    static class TrajectoryPoint {
        final String deviceId;
        final double latitude;
        final double longitude;
        final double altitude;
        final double heading;
        final double speed;
        final double batteryLevel;
        final String status;
        final Instant timestamp;

        TrajectoryPoint(String deviceId, double latitude, double longitude, double altitude,
                        double heading, double speed, double batteryLevel, String status,
                        Instant timestamp) {
            this.deviceId = deviceId;
            this.latitude = latitude;
            this.longitude = longitude;
            this.altitude = altitude;
            this.heading = heading;
            this.speed = speed;
            this.batteryLevel = batteryLevel;
            this.status = status;
            this.timestamp = timestamp;
        }
    }

    static class GeoFence {
        final String fenceId;
        final String name;
        final double centerLat;
        final double centerLon;
        final double radiusMeters;
        final String alertType; // "enter", "exit", "both"
        Instant lastTriggered;

        GeoFence(String fenceId, String name, double centerLat, double centerLon,
                 double radiusMeters, String alertType) {
            this.fenceId = fenceId;
            this.name = name;
            this.centerLat = centerLat;
            this.centerLon = centerLon;
            this.radiusMeters = radiusMeters;
            this.alertType = alertType;
        }
    }
}
