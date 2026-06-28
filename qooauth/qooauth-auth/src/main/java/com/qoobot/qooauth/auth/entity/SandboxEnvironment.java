package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * Sandbox Environment for developer testing.
 *
 * Provides isolated authentication environments where developers
 * can test their skills without affecting production systems.
 * Each sandbox has resource quotas and time limits.
 */
@Entity
@Table(name = "sandbox_environments", indexes = {
    @Index(name = "idx_se_user", columnList = "userId"),
    @Index(name = "idx_se_state", columnList = "state")
})
public class SandboxEnvironment {

    @Id
    @Column(name = "env_id", length = 64)
    private String envId;

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    /**
     * Human-readable name for the sandbox.
     */
    @Column(name = "name", nullable = false, length = 128)
    private String name;

    /**
     * Sandbox state: ACTIVE, SUSPENDED, TERMINATED, EXPIRED
     */
    @Column(name = "state", nullable = false, length = 16)
    private String state = "ACTIVE";

    /**
     * Resource limits as JSON:
     * { "max_robots": 5, "max_api_calls_per_hour": 1000,
     *   "max_storage_mb": 500, "allowed_scopes": ["read", "skill_test"] }
     */
    @Column(name = "resource_limits", nullable = false, columnDefinition = "TEXT")
    private String resourceLimits;

    /**
     * Current resource usage as JSON:
     * { "robot_count": 1, "api_calls_this_hour": 42, "storage_used_mb": 120 }
     */
    @Column(name = "resource_usage", columnDefinition = "TEXT")
    private String resourceUsage;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "expires_at")
    private Instant expiresAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    // --- Getters and Setters ---

    public String getEnvId() { return envId; }
    public void setEnvId(String envId) { this.envId = envId; }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getState() { return state; }
    public void setState(String state) { this.state = state; }

    public String getResourceLimits() { return resourceLimits; }
    public void setResourceLimits(String resourceLimits) { this.resourceLimits = resourceLimits; }

    public String getResourceUsage() { return resourceUsage; }
    public void setResourceUsage(String resourceUsage) { this.resourceUsage = resourceUsage; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getExpiresAt() { return expiresAt; }
    public void setExpiresAt(Instant expiresAt) { this.expiresAt = expiresAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
