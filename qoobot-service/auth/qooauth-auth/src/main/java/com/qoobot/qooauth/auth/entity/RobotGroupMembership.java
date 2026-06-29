package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * Represents a robot's membership in a trust group.
 * Each robot can belong to multiple groups with potentially
 * different roles and capability grants.
 */
@Entity
@Table(name = "robot_group_memberships", indexes = {
    @Index(name = "idx_rgm_group", columnList = "groupId"),
    @Index(name = "idx_rgm_device", columnList = "deviceId"),
    @Index(name = "idx_rgm_state", columnList = "state")
}, uniqueConstraints = {
    @UniqueConstraint(name = "uk_rgm_group_device", columnNames = {"groupId", "deviceId"})
})
public class RobotGroupMembership {

    @Id
    @Column(name = "membership_id", length = 64)
    private String membershipId;

    @Column(name = "group_id", nullable = false, length = 64)
    private String groupId;

    @Column(name = "device_id", nullable = false, length = 64)
    private String deviceId;

    @Column(name = "user_id", length = 64)
    private String userId;

    /**
     * Role within the group: LEADER, MEMBER, OBSERVER
     */
    @Column(name = "role", nullable = false, length = 16)
    private String role = "MEMBER";

    /**
     * Membership state: ACTIVE, SUSPENDED, REMOVED
     */
    @Column(name = "state", nullable = false, length = 16)
    private String state = "ACTIVE";

    /**
     * Specific capability grants for this member as JSON:
     * ["task_delegation", "sensor_sharing", "joint_planning"]
     */
    @Column(name = "capability_grants", columnDefinition = "TEXT")
    private String capabilityGrants;

    @Column(name = "joined_at", nullable = false)
    private Instant joinedAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @Column(name = "left_at")
    private Instant leftAt;

    // --- Getters and Setters ---

    public String getMembershipId() { return membershipId; }
    public void setMembershipId(String membershipId) { this.membershipId = membershipId; }

    public String getGroupId() { return groupId; }
    public void setGroupId(String groupId) { this.groupId = groupId; }

    public String getDeviceId() { return deviceId; }
    public void setDeviceId(String deviceId) { this.deviceId = deviceId; }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }

    public String getState() { return state; }
    public void setState(String state) { this.state = state; }

    public String getCapabilityGrants() { return capabilityGrants; }
    public void setCapabilityGrants(String capabilityGrants) { this.capabilityGrants = capabilityGrants; }

    public Instant getJoinedAt() { return joinedAt; }
    public void setJoinedAt(Instant joinedAt) { this.joinedAt = joinedAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }

    public Instant getLeftAt() { return leftAt; }
    public void setLeftAt(Instant leftAt) { this.leftAt = leftAt; }
}
