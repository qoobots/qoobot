package com.qoobot.qoocloud.infra.controller;

import com.qoobot.qoocloud.infra.service.CloudInfraService;
import com.qoobot.qoocloud.infra.service.MultiRegionService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST API for cloud infrastructure: tenants, scaling, DR, multi-region, API gateway.
 */
@RestController
@RequestMapping("/api/v1/infra")
public class InfraController {

    private final CloudInfraService cloudInfraService;
    private final MultiRegionService multiRegionService;

    public InfraController(CloudInfraService cloudInfraService,
                            MultiRegionService multiRegionService) {
        this.cloudInfraService = cloudInfraService;
        this.multiRegionService = multiRegionService;
    }

    // ================================================================
    // 多租户管理
    // ================================================================

    @PostMapping("/tenants")
    public ResponseEntity<CloudInfraService.Tenant> createTenant(@RequestBody Map<String, Object> body) {
        String name = (String) body.get("name");
        String tier = (String) body.getOrDefault("tier", "free");
        return ResponseEntity.ok(cloudInfraService.createTenant(name, tier));
    }

    @GetMapping("/tenants")
    public ResponseEntity<List<CloudInfraService.Tenant>> listTenants() {
        return ResponseEntity.ok(cloudInfraService.listTenants());
    }

    @GetMapping("/tenants/{tenantId}")
    public ResponseEntity<CloudInfraService.Tenant> getTenant(@PathVariable String tenantId) {
        CloudInfraService.Tenant tenant = cloudInfraService.getTenant(tenantId);
        return tenant != null ? ResponseEntity.ok(tenant) : ResponseEntity.notFound().build();
    }

    @PostMapping("/tenants/{tenantId}/suspend")
    public ResponseEntity<Void> suspendTenant(
            @PathVariable String tenantId,
            @RequestBody Map<String, String> body) {
        cloudInfraService.suspendTenant(tenantId, body.getOrDefault("reason", "Manual suspension"));
        return ResponseEntity.ok().build();
    }

    @PostMapping("/tenants/{tenantId}/reactivate")
    public ResponseEntity<Void> reactivateTenant(@PathVariable String tenantId) {
        cloudInfraService.reactivateTenant(tenantId);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/tenants/{tenantId}/quota/check")
    public ResponseEntity<Map<String, Boolean>> checkQuota(
            @PathVariable String tenantId,
            @RequestBody Map<String, Object> body) {
        String resourceType = (String) body.get("resourceType");
        long currentUsage = ((Number) body.get("currentUsage")).longValue();
        return ResponseEntity.ok(Map.of(
                "exceeded", cloudInfraService.isQuotaExceeded(tenantId, resourceType, currentUsage)));
    }

    // ================================================================
    // 弹性伸缩
    // ================================================================

    @PostMapping("/scaling/policies")
    public ResponseEntity<Void> registerScalingPolicy(@RequestBody Map<String, Object> body) {
        String serviceName = (String) body.get("serviceName");
        CloudInfraService.ScalingPolicy policy = new CloudInfraService.ScalingPolicy();
        policy.minInstances = ((Number) body.getOrDefault("minInstances", 1)).intValue();
        policy.maxInstances = ((Number) body.getOrDefault("maxInstances", 10)).intValue();
        policy.scaleUpThreshold = ((Number) body.getOrDefault("scaleUpThreshold", 0.7)).doubleValue();
        policy.scaleDownThreshold = ((Number) body.getOrDefault("scaleDownThreshold", 0.3)).doubleValue();
        policy.scaleUpStep = ((Number) body.getOrDefault("scaleUpStep", 2)).intValue();
        policy.scaleDownStep = ((Number) body.getOrDefault("scaleDownStep", 1)).intValue();
        policy.cooldownSeconds = ((Number) body.getOrDefault("cooldownSeconds", 300)).intValue();
        cloudInfraService.registerScalingPolicy(serviceName, policy);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/scaling/evaluate")
    public ResponseEntity<CloudInfraService.ScalingDecision> evaluateScaling(
            @RequestBody Map<String, Object> body) {
        String serviceName = (String) body.get("serviceName");
        double currentLoad = ((Number) body.get("currentLoad")).doubleValue();
        int currentInstances = ((Number) body.get("currentInstances")).intValue();
        return ResponseEntity.ok(cloudInfraService.evaluateScaling(
                serviceName, currentLoad, currentInstances));
    }

    // ================================================================
    // 灾备恢复
    // ================================================================

    @PostMapping("/dr/plans")
    public ResponseEntity<CloudInfraService.DisasterRecoveryPlan> createDRPlan(
            @RequestBody Map<String, Object> body) {
        String name = (String) body.get("name");
        String primaryRegion = (String) body.get("primaryRegion");
        String backupRegion = (String) body.get("backupRegion");
        int rpoMinutes = ((Number) body.getOrDefault("rpoMinutes", 5)).intValue();
        return ResponseEntity.ok(cloudInfraService.createDRPlan(
                name, primaryRegion, backupRegion, rpoMinutes));
    }

    @GetMapping("/dr/plans")
    public ResponseEntity<List<CloudInfraService.DisasterRecoveryPlan>> getDRPlans() {
        return ResponseEntity.ok(cloudInfraService.getDRPlans());
    }

    @PostMapping("/dr/plans/{planId}/failover")
    public ResponseEntity<Map<String, String>> triggerFailover(@PathVariable String planId) {
        return ResponseEntity.ok(Map.of("result", cloudInfraService.triggerFailover(planId)));
    }

    @PostMapping("/dr/plans/{planId}/failback")
    public ResponseEntity<Map<String, String>> triggerFailback(@PathVariable String planId) {
        return ResponseEntity.ok(Map.of("result", cloudInfraService.triggerFailback(planId)));
    }

    // ================================================================
    // API 网关管理
    // ================================================================

    @GetMapping("/gateway/rate-limit")
    public ResponseEntity<Map<String, Object>> getRateLimitConfig() {
        return ResponseEntity.ok(cloudInfraService.getRateLimitConfig());
    }

    @PostMapping("/gateway/api-key/validate")
    public ResponseEntity<Map<String, Boolean>> validateApiKey(
            @RequestBody Map<String, String> body) {
        return ResponseEntity.ok(Map.of(
                "valid", cloudInfraService.validateApiKey(body.get("apiKey"))));
    }

    // ================================================================
    // 健康状态
    // ================================================================

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> getHealth() {
        return ResponseEntity.ok(cloudInfraService.getHealthStatus());
    }

    // ================================================================
    // 多区域部署
    // ================================================================

    @GetMapping("/regions")
    public ResponseEntity<List<MultiRegionService.Region>> listRegions() {
        return ResponseEntity.ok(multiRegionService.listRegions());
    }

    @GetMapping("/regions/{regionCode}")
    public ResponseEntity<MultiRegionService.Region> getRegion(@PathVariable String regionCode) {
        return multiRegionService.getRegion(regionCode)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/regions/nearest")
    public ResponseEntity<MultiRegionService.Region> getNearestRegion(
            @RequestParam double lat, @RequestParam double lng) {
        MultiRegionService.Region region = multiRegionService.getNearestRegion(lat, lng);
        return region != null ? ResponseEntity.ok(region) : ResponseEntity.notFound().build();
    }

    @GetMapping("/regions/optimal")
    public ResponseEntity<List<MultiRegionService.RegionLatency>> getOptimalRegions(
            @RequestParam double lat, @RequestParam double lng,
            @RequestParam(defaultValue = "3") int limit) {
        return ResponseEntity.ok(multiRegionService.getOptimalRegions(lat, lng, limit));
    }

    @GetMapping("/regions/latency-matrix")
    public ResponseEntity<Map<String, Map<String, Long>>> getLatencyMatrix() {
        return ResponseEntity.ok(multiRegionService.getLatencyMatrix());
    }

    @PostMapping("/regions/{regionCode}/status")
    public ResponseEntity<Void> setRegionStatus(
            @PathVariable String regionCode,
            @RequestBody Map<String, String> body) {
        multiRegionService.setRegionStatus(regionCode, body.get("status"));
        return ResponseEntity.ok().build();
    }

    @GetMapping("/regions/health")
    public ResponseEntity<MultiRegionService.MultiRegionHealth> getMultiRegionHealth() {
        return ResponseEntity.ok(multiRegionService.getMultiRegionHealth());
    }

    @PostMapping("/replication/policies")
    public ResponseEntity<MultiRegionService.ReplicationPolicy> createReplicationPolicy(
            @RequestBody Map<String, Object> body) {
        String policyName = (String) body.get("policyName");
        String sourceRegion = (String) body.get("sourceRegion");
        @SuppressWarnings("unchecked")
        List<String> targetRegions = (List<String>) body.get("targetRegions");
        MultiRegionService.ReplicationMode mode = MultiRegionService.ReplicationMode.valueOf(
                (String) body.getOrDefault("mode", "ASYNC"));
        int rpoSeconds = ((Number) body.getOrDefault("rpoSeconds", 300)).intValue();
        return ResponseEntity.ok(multiRegionService.createReplicationPolicy(
                policyName, sourceRegion, targetRegions, mode, rpoSeconds));
    }

    @GetMapping("/replication/policies")
    public ResponseEntity<List<MultiRegionService.ReplicationPolicy>> listReplicationPolicies() {
        return ResponseEntity.ok(multiRegionService.listReplicationPolicies());
    }
}
