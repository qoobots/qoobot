package com.qoobot.qoocloud.infra.service;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * CloudInfraService — 云基础设施服务
 * 多租户隔离、弹性伸缩、多区域部署、灾备恢复、API 网关
 */
@Service
public class CloudInfraService {

    private final Map<String, Tenant> tenants = new ConcurrentHashMap<>();
    private final Map<String, ResourceQuota> quotas = new ConcurrentHashMap<>();
    private final Map<String, ScalingPolicy> scalingPolicies = new ConcurrentHashMap<>();
    private final List<DisasterRecoveryPlan> drPlans = new ArrayList<>();

    // ========================================================================
    // Multi-Tenant Isolation
    // ========================================================================

    /**
     * Create a new tenant.
     */
    public Tenant createTenant(String name, String tier) {
        String tenantId = "tenant_" + UUID.randomUUID().toString().substring(0, 8);
        Tenant tenant = new Tenant();
        tenant.tenantId = tenantId;
        tenant.name = name;
        tenant.tier = tier;
        tenant.createdAt = Instant.now();
        tenant.status = "active";

        // Default quotas based on tier
        ResourceQuota quota = new ResourceQuota();
        switch (tier) {
            case "free":
                quota.maxDevices = 5;
                quota.maxInferenceRequestsPerDay = 1000;
                quota.maxStorageGB = 1;
                quota.maxConcurrentConnections = 2;
                break;
            case "pro":
                quota.maxDevices = 50;
                quota.maxInferenceRequestsPerDay = 50000;
                quota.maxStorageGB = 50;
                quota.maxConcurrentConnections = 20;
                break;
            case "enterprise":
                quota.maxDevices = Integer.MAX_VALUE;
                quota.maxInferenceRequestsPerDay = Long.MAX_VALUE;
                quota.maxStorageGB = 1000;
                quota.maxConcurrentConnections = 500;
                break;
            default:
                quota.maxDevices = 1;
                quota.maxInferenceRequestsPerDay = 100;
                quota.maxStorageGB = 0.1;
                quota.maxConcurrentConnections = 1;
        }

        tenants.put(tenantId, tenant);
        quotas.put(tenantId, quota);

        return tenant;
    }

    /**
     * Check if a tenant has exceeded their quota.
     */
    public boolean isQuotaExceeded(String tenantId, String resourceType, long currentUsage) {
        ResourceQuota quota = quotas.get(tenantId);
        if (quota == null) return true;

        return switch (resourceType) {
            case "devices" -> currentUsage >= quota.maxDevices;
            case "inference" -> currentUsage >= quota.maxInferenceRequestsPerDay;
            case "storage" -> currentUsage >= quota.maxStorageGB;
            case "connections" -> currentUsage >= quota.maxConcurrentConnections;
            default -> false;
        };
    }

    /**
     * Update tenant quota.
     */
    public void updateQuota(String tenantId, ResourceQuota newQuota) {
        quotas.put(tenantId, newQuota);
    }

    /**
     * Get tenant info.
     */
    public Tenant getTenant(String tenantId) {
        return tenants.get(tenantId);
    }

    /**
     * List all tenants.
     */
    public List<Tenant> listTenants() {
        return new ArrayList<>(tenants.values());
    }

    /**
     * Suspend a tenant.
     */
    public void suspendTenant(String tenantId, String reason) {
        Tenant tenant = tenants.get(tenantId);
        if (tenant != null) {
            tenant.status = "suspended";
            tenant.suspensionReason = reason;
        }
    }

    /**
     * Reactivate a tenant.
     */
    public void reactivateTenant(String tenantId) {
        Tenant tenant = tenants.get(tenantId);
        if (tenant != null) {
            tenant.status = "active";
            tenant.suspensionReason = null;
        }
    }

    // ========================================================================
    // Elastic Scaling
    // ========================================================================

    /**
     * Register a scaling policy for a service.
     */
    public void registerScalingPolicy(String serviceName, ScalingPolicy policy) {
        policy.serviceName = serviceName;
        scalingPolicies.put(serviceName, policy);
    }

    /**
     * Evaluate scaling needs based on current metrics.
     */
    public ScalingDecision evaluateScaling(String serviceName, double currentLoad,
                                            int currentInstances) {
        ScalingPolicy policy = scalingPolicies.get(serviceName);
        if (policy == null) {
            return new ScalingDecision("no_policy", 0, "No scaling policy defined");
        }

        if (currentLoad > policy.scaleUpThreshold && currentInstances < policy.maxInstances) {
            int scaleBy = Math.min(policy.scaleUpStep, policy.maxInstances - currentInstances);
            return new ScalingDecision("scale_up", scaleBy,
                String.format("Load %.2f > threshold %.2f", currentLoad, policy.scaleUpThreshold));
        }

        if (currentLoad < policy.scaleDownThreshold && currentInstances > policy.minInstances) {
            int scaleBy = Math.min(policy.scaleDownStep, currentInstances - policy.minInstances);
            return new ScalingDecision("scale_down", -scaleBy,
                String.format("Load %.2f < threshold %.2f", currentLoad, policy.scaleDownThreshold));
        }

        return new ScalingDecision("stable", 0, "Load within acceptable range");
    }

    // ========================================================================
    // Disaster Recovery
    // ========================================================================

    /**
     * Create a disaster recovery plan.
     */
    public DisasterRecoveryPlan createDRPlan(String name, String primaryRegion,
                                              String backupRegion, int rpoMinutes) {
        DisasterRecoveryPlan plan = new DisasterRecoveryPlan();
        plan.planId = "drp_" + UUID.randomUUID().toString().substring(0, 8);
        plan.name = name;
        plan.primaryRegion = primaryRegion;
        plan.backupRegion = backupRegion;
        plan.rpoMinutes = rpoMinutes;
        plan.status = "active";
        plan.createdAt = Instant.now();
        drPlans.add(plan);
        return plan;
    }

    /**
     * Trigger failover to backup region.
     */
    public String triggerFailover(String planId) {
        for (DisasterRecoveryPlan plan : drPlans) {
            if (plan.planId.equals(planId)) {
                plan.lastFailoverAt = Instant.now();
                plan.status = "failed_over";
                return String.format("Failover to %s initiated", plan.backupRegion);
            }
        }
        return "DR plan not found";
    }

    /**
     * Trigger failback to primary region.
     */
    public String triggerFailback(String planId) {
        for (DisasterRecoveryPlan plan : drPlans) {
            if (plan.planId.equals(planId)) {
                plan.lastFailbackAt = Instant.now();
                plan.status = "active";
                return String.format("Failback to %s completed", plan.primaryRegion);
            }
        }
        return "DR plan not found";
    }

    /**
     * Get all DR plans.
     */
    public List<DisasterRecoveryPlan> getDRPlans() {
        return new ArrayList<>(drPlans);
    }

    // ========================================================================
    // API Gateway Management
    // ========================================================================

    /**
     * Get current rate limit configuration.
     */
    public Map<String, Object> getRateLimitConfig() {
        Map<String, Object> config = new HashMap<>();
        config.put("defaultLimit", 100);
        config.put("defaultWindowSeconds", 60);
        config.put("burstMultiplier", 2.0);
        return config;
    }

    /**
     * Validate an API key.
     */
    public boolean validateApiKey(String apiKey) {
        // In production: check against database of active API keys
        return apiKey != null && apiKey.startsWith("qoo_");
    }

    /**
     * Get infrastructure health status.
     */
    public Map<String, Object> getHealthStatus() {
        Map<String, Object> health = new HashMap<>();
        health.put("status", "healthy");
        health.put("activeTenants", tenants.values().stream()
            .filter(t -> "active".equals(t.status)).count());
        health.put("suspendedTenants", tenants.values().stream()
            .filter(t -> "suspended".equals(t.status)).count());
        health.put("drPlansActive", drPlans.stream()
            .filter(p -> "active".equals(p.status)).count());
        health.put("scalingPolicies", scalingPolicies.size());
        health.put("timestamp", Instant.now().toString());
        return health;
    }

    // ========================================================================
    // Inner Types
    // ========================================================================

    public static class Tenant {
        public String tenantId;
        public String name;
        public String tier;
        public String status;
        public String suspensionReason;
        public Instant createdAt;
    }

    public static class ResourceQuota {
        public int maxDevices;
        public long maxInferenceRequestsPerDay;
        public double maxStorageGB;
        public int maxConcurrentConnections;
    }

    public static class ScalingPolicy {
        public String serviceName;
        public int minInstances = 1;
        public int maxInstances = 10;
        public double scaleUpThreshold = 0.7;
        public double scaleDownThreshold = 0.3;
        public int scaleUpStep = 2;
        public int scaleDownStep = 1;
        public int cooldownSeconds = 300;
    }

    public static class ScalingDecision {
        public String action;
        public int instanceChange;
        public String reason;

        public ScalingDecision(String action, int change, String reason) {
            this.action = action;
            this.instanceChange = change;
            this.reason = reason;
        }
    }

    public static class DisasterRecoveryPlan {
        public String planId;
        public String name;
        public String primaryRegion;
        public String backupRegion;
        public int rpoMinutes;
        public String status;
        public Instant createdAt;
        public Instant lastFailoverAt;
        public Instant lastFailbackAt;
    }
}
