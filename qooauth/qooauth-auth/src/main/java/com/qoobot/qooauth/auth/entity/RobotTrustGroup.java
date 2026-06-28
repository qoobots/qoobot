package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * Represents a group of robots that mutually trust each other.
 * Members within a group can collaborate on tasks without
 * requiring individual pairwise authorization.
 */
@Entity
@Table(name = "robot_trust_groups", indexes = {
    @Index(name = "idx_rtg_owner", columnList = "ownerUserId"),
    @Index(name = "idx_rtg_state", columnList = "state")
})
public class RobotTrustGroup {

    @Id
    @Column(name = "group_id", length = 64)
    private String groupId;

    @Column(name = "name", nullable = false, length = 128)
    private String name;

    @Column(name = "description", columnDefinition = "TEXT")
    private String description;

    @Column(name = "owner_user_id", nullable = false, length = 64)
    private String ownerUserId;

    /**
     * Group state: ACTIVE, DISSOLVED, SUSPENDED
     */
    @Column(name = "state", nullable = false, length = 16)
    private String state = "ACTIVE";

    /**
     * Maximum number of members allowed in this group.
     */
    @Column(name = "max_members")
    private Integer maxMembers = 50;

    /**
     * Group-level trust policy as JSON:
     * { "allow_task_delegation": true, "allow_sensor_sharing": true,
     *   "require_peer_attestation": true, "max_delegation_depth": 3 }
     */
    @Column(name = "trust_policy", columnDefinition = "TEXT")
    private String trustPolicy;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @Column(name = "dissolved_at")
    private Instant dissolvedAt;

    // --- Getters and Setters ---

    public String getGroupId() { return groupId; }
    public void setGroupId(String groupId) { this.groupId = groupId; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public String getOwnerUserId() { return ownerUserId; }
    public void setOwnerUserId(String ownerUserId) { this.ownerUserId = ownerUserId; }

    public String getState() { return state; }
    public void setState(String state) { this.state = state; }

    public Integer getMaxMembers() { return maxMembers; }
    public void setMaxMembers(Integer maxMembers) { this.maxMembers = maxMembers; }

    public String getTrustPolicy() { return trustPolicy; }
    public void setTrustPolicy(String trustPolicy) { this.trustPolicy = trustPolicy; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }

    public Instant getDissolvedAt() { return dissolvedAt; }
    public void setDissolvedAt(Instant dissolvedAt) { this.dissolvedAt = dissolvedAt; }
}
