package com.qoobot.qoocloud.infra.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * MultiRegionService — 多区域部署服务
 * 全球多区域部署，就近接入降低延迟，跨区域数据同步
 */
@Service
public class MultiRegionService {

    private static final Logger log = LoggerFactory.getLogger(MultiRegionService.class);

    // 区域注册
    private final Map<String, Region> regions = new ConcurrentHashMap<>();
    // 区域间延迟矩阵
    private final Map<String, Map<String, Long>> latencyMatrix = new ConcurrentHashMap<>();
    // 数据同步策略
    private final Map<String, ReplicationPolicy> replicationPolicies = new ConcurrentHashMap<>();

    public MultiRegionService() {
        initializeDefaultRegions();
    }

    /**
     * 初始化默认区域。
     */
    private void initializeDefaultRegions() {
        registerRegion("cn-beijing", "China Beijing", "asia-east", 39.9, 116.4, "active");
        registerRegion("cn-shanghai", "China Shanghai", "asia-east", 31.2, 121.5, "active");
        registerRegion("cn-guangzhou", "China Guangzhou", "asia-south", 23.1, 113.3, "active");
        registerRegion("us-west", "US West (Oregon)", "americas-west", 45.5, -122.7, "active");
        registerRegion("us-east", "US East (Virginia)", "americas-east", 38.9, -77.0, "active");
        registerRegion("eu-frankfurt", "EU Frankfurt", "europe-west", 50.1, 8.7, "active");
        registerRegion("ap-singapore", "Asia Pacific Singapore", "asia-southeast", 1.3, 103.8, "active");
        registerRegion("ap-tokyo", "Asia Pacific Tokyo", "asia-northeast", 35.7, 139.7, "active");

        // 建立默认延迟矩阵（估算值，单位 ms）
        buildDefaultLatencyMatrix();

        // 默认复制策略
        replicationPolicies.put("default", createDefaultReplicationPolicy());
    }

    /**
     * 注册区域。
     */
    public Region registerRegion(String regionCode, String displayName,
                                   String geoZone, double lat, double lng, String status) {
        Region region = new Region();
        region.regionCode = regionCode;
        region.displayName = displayName;
        region.geoZone = geoZone;
        region.latitude = lat;
        region.longitude = lng;
        region.status = status;
        region.registeredAt = Instant.now();

        regions.put(regionCode, region);
        log.info("Region registered: {} ({})", regionCode, displayName);
        return region;
    }

    /**
     * 获取距离设备最近的区域。
     */
    public Region getNearestRegion(double deviceLat, double deviceLng) {
        Region nearest = null;
        double minDistance = Double.MAX_VALUE;

        for (Region region : regions.values()) {
            if ("active".equals(region.status)) {
                double distance = haversineDistance(deviceLat, deviceLng,
                        region.latitude, region.longitude);
                if (distance < minDistance) {
                    minDistance = distance;
                    nearest = region;
                }
            }
        }

        return nearest;
    }

    /**
     * 获取最优区域列表（按延迟排序）。
     */
    public List<RegionLatency> getOptimalRegions(double deviceLat, double deviceLng, int limit) {
        List<RegionLatency> results = new ArrayList<>();

        for (Region region : regions.values()) {
            if ("active".equals(region.status)) {
                double distance = haversineDistance(deviceLat, deviceLng,
                        region.latitude, region.longitude);
                // 粗略延迟估算：光速在光纤中的传播 ≈ 200km/ms + 10ms 路由延迟
                long estimatedLatency = (long) (distance * 1000 / 200) + 10;
                results.add(new RegionLatency(region.regionCode, region.displayName,
                        distance, estimatedLatency));
            }
        }

        results.sort(Comparator.comparingLong(RegionLatency::estimatedLatencyMs));
        return results.subList(0, Math.min(limit, results.size()));
    }

    /**
     * 获取区域间延迟。
     */
    public long getInterRegionLatency(String fromRegion, String toRegion) {
        Map<String, Long> fromLatencies = latencyMatrix.get(fromRegion);
        if (fromLatencies != null) {
            Long latency = fromLatencies.get(toRegion);
            if (latency != null) return latency;
        }
        return -1;
    }

    /**
     * 设置区域间延迟。
     */
    public void setInterRegionLatency(String fromRegion, String toRegion, long latencyMs) {
        latencyMatrix.computeIfAbsent(fromRegion, k -> new ConcurrentHashMap<>())
                .put(toRegion, latencyMs);
        // 对称设置
        latencyMatrix.computeIfAbsent(toRegion, k -> new ConcurrentHashMap<>())
                .put(fromRegion, latencyMs);
    }

    /**
     * 创建数据复制策略。
     */
    public ReplicationPolicy createReplicationPolicy(String policyName, String sourceRegion,
                                                       List<String> targetRegions,
                                                       ReplicationMode mode, int rpoSeconds) {
        String policyId = "rep_" + UUID.randomUUID().toString().substring(0, 8);

        ReplicationPolicy policy = new ReplicationPolicy();
        policy.policyId = policyId;
        policy.policyName = policyName;
        policy.sourceRegion = sourceRegion;
        policy.targetRegions = targetRegions;
        policy.mode = mode;
        policy.rpoSeconds = rpoSeconds;
        policy.status = "active";
        policy.createdAt = Instant.now();

        replicationPolicies.put(policyId, policy);
        log.info("Replication policy created: {} ({} → {})",
                policyName, sourceRegion, targetRegions);
        return policy;
    }

    /**
     * 评估多区域部署的健康状态。
     */
    public MultiRegionHealth getMultiRegionHealth() {
        MultiRegionHealth health = new MultiRegionHealth();
        health.timestamp = Instant.now();

        List<MultiRegionHealth.RegionHealth> regionHealths = new ArrayList<>();
        for (Region region : regions.values()) {
            MultiRegionHealth.RegionHealth rh = new MultiRegionHealth.RegionHealth();
            rh.regionCode = region.regionCode;
            rh.displayName = region.displayName;
            rh.status = region.status;
            rh.activeReplications = (int) replicationPolicies.values().stream()
                    .filter(p -> p.sourceRegion.equals(region.regionCode) &&
                            "active".equals(p.status))
                    .count();
            regionHealths.add(rh);
        }

        health.regions = regionHealths;
        health.activeRegions = (int) regions.values().stream()
                .filter(r -> "active".equals(r.status)).count();
        health.totalRegions = regions.size();
        health.activeReplicationPolicies = (int) replicationPolicies.values().stream()
                .filter(p -> "active".equals(p.status)).count();

        return health;
    }

    /**
     * 列出所有区域。
     */
    public List<Region> listRegions() {
        return new ArrayList<>(regions.values());
    }

    /**
     * 获取区域详情。
     */
    public Optional<Region> getRegion(String regionCode) {
        return Optional.ofNullable(regions.get(regionCode));
    }

    /**
     * 启用/禁用区域。
     */
    public void setRegionStatus(String regionCode, String status) {
        Region region = regions.get(regionCode);
        if (region != null) {
            region.status = status;
            log.info("Region {} status changed to {}", regionCode, status);
        }
    }

    /**
     * 获取区域延迟矩阵。
     */
    public Map<String, Map<String, Long>> getLatencyMatrix() {
        return Map.copyOf(latencyMatrix);
    }

    /**
     * 列出所有复制策略。
     */
    public List<ReplicationPolicy> listReplicationPolicies() {
        return new ArrayList<>(replicationPolicies.values());
    }

    /**
     * 构建默认延迟矩阵。
     */
    private void buildDefaultLatencyMatrix() {
        String[][] pairs = {
                {"cn-beijing", "cn-shanghai", "20"},
                {"cn-beijing", "cn-guangzhou", "35"},
                {"cn-shanghai", "cn-guangzhou", "25"},
                {"cn-beijing", "ap-tokyo", "50"},
                {"cn-shanghai", "ap-tokyo", "40"},
                {"cn-beijing", "ap-singapore", "80"},
                {"cn-shanghai", "ap-singapore", "70"},
                {"us-west", "us-east", "60"},
                {"us-west", "ap-tokyo", "120"},
                {"us-east", "eu-frankfurt", "90"},
                {"eu-frankfurt", "ap-singapore", "160"},
                {"eu-frankfurt", "cn-beijing", "170"},
        };

        for (String[] pair : pairs) {
            setInterRegionLatency(pair[0], pair[1], Long.parseLong(pair[2]));
        }
    }

    private ReplicationPolicy createDefaultReplicationPolicy() {
        ReplicationPolicy policy = new ReplicationPolicy();
        policy.policyId = "rep_default";
        policy.policyName = "Default Cross-Region Replication";
        policy.sourceRegion = "cn-beijing";
        policy.targetRegions = List.of("cn-shanghai", "us-west", "eu-frankfurt");
        policy.mode = ReplicationMode.ASYNC;
        policy.rpoSeconds = 300; // 5 minutes
        policy.status = "active";
        policy.createdAt = Instant.now();
        return policy;
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

    public enum ReplicationMode {
        SYNC,     // 同步复制：写入主区域确认前必须复制到所有目标
        ASYNC,    // 异步复制：写入主区域后异步复制
        SEMI_SYNC // 半同步：至少一个目标区域确认即可
    }

    public static class Region {
        public String regionCode;
        public String displayName;
        public String geoZone;
        public double latitude;
        public double longitude;
        public String status;      // active, inactive, maintenance
        public Instant registeredAt;
    }

    public record RegionLatency(
            String regionCode,
            String displayName,
            double distanceKm,
            long estimatedLatencyMs
    ) {}

    public static class ReplicationPolicy {
        public String policyId;
        public String policyName;
        public String sourceRegion;
        public List<String> targetRegions = new ArrayList<>();
        public ReplicationMode mode;
        public int rpoSeconds;
        public String status;
        public Instant createdAt;
    }

    public static class MultiRegionHealth {
        public Instant timestamp;
        public int activeRegions;
        public int totalRegions;
        public int activeReplicationPolicies;
        public List<RegionHealth> regions = new ArrayList<>();

        public static class RegionHealth {
            public String regionCode;
            public String displayName;
            public String status;
            public int activeReplications;
        }
    }
}
