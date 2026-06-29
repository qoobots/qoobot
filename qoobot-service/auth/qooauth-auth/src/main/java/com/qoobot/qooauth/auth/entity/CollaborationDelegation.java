package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * Represents a collaboration delegation token issued by one robot
 * to another, granting specific capabilities for a limited time.
 */
@Entity
@Table(name = "collaboration_delegations", indexes = {
    @Index(name = "idx_cd_delegator", columnList = "delegatorDeviceId"),
    @Index(name = "idx_cd_delegate", columnList = "delegateDeviceId"),
    @Index(name = "idx_cd_token_hash", columnList = "tokenHash"),
    @Index(name = "idx_cd_expires", columnList = "expiresAt")
})
public class CollaborationDelegation {

    @Id
    @Column(name = "delegation_id", length = 64)
    private String delegationId;

    /**
     * SHA-256 hash of the delegation token.
     */
    @Column(name = "token_hash", nullable = false, length = 128, unique = true)
    private String tokenHash;

    @Column(name = "delegator_device_id", nullable = false, length = 64)
    private String delegatorDeviceId;

    @Column(name = "delegator_user_id", length = 64)
    private String delegatorUserId;

    @Column(name = "delegate_device_id", nullable = false, length = 64)
    private String delegateDeviceId;

    @Column(name = "delegate_user_id", length = 64)
    private String delegateUserId;

    /**
     * Delegated capabilities as JSON array:
     * ["joint_navigation", "sensor_data_access", "task_coordination"]
     */
    @Column(name = "capabilities", nullable = false, columnDefinition = "TEXT")
    private String capabilities;

    /**
     * Token state: ACTIVE, REVOKED, EXPIRED
     */
    @Column(name = "state", nullable = false, length = 16)
    private String state = "ACTIVE";

    @Column(name = "issued_at", nullable = false)
    private Instant issuedAt;

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    @Column(name = "revoked_at")
    private Instant revokedAt;

    @Column(name = "revoke_reason", length = 256)
    private String revokeReason;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    // --- Getters and Setters ---

    public String getDelegationId() { return delegationId; }
    public void setDelegationId(String delegationId) { this.delegationId = delegationId; }

    public String getTokenHash() { return tokenHash; }
    public void setTokenHash(String tokenHash) { this.tokenHash = tokenHash; }

    public String getDelegatorDeviceId() { return delegatorDeviceId; }
    public void setDelegatorDeviceId(String delegatorDeviceId) { this.delegatorDeviceId = delegatorDeviceId; }

    public String getDelegatorUserId() { return delegatorUserId; }
    public void setDelegatorUserId(String delegatorUserId) { this.delegatorUserId = delegatorUserId; }

    public String getDelegateDeviceId() { return delegateDeviceId; }
    public void setDelegateDeviceId(String delegateDeviceId) { this.delegateDeviceId = delegateDeviceId; }

    public String getDelegateUserId() { return delegateUserId; }
    public void setDelegateUserId(String delegateUserId) { this.delegateUserId = delegateUserId; }

    public String getCapabilities() { return capabilities; }
    public void setCapabilities(String capabilities) { this.capabilities = capabilities; }

    public String getState() { return state; }
    public void setState(String state) { this.state = state; }

    public Instant getIssuedAt() { return issuedAt; }
    public void setIssuedAt(Instant issuedAt) { this.issuedAt = issuedAt; }

    public Instant getExpiresAt() { return expiresAt; }
    public void setExpiresAt(Instant expiresAt) { this.expiresAt = expiresAt; }

    public Instant getRevokedAt() { return revokedAt; }
    public void setRevokedAt(Instant revokedAt) { this.revokedAt = revokedAt; }

    public String getRevokeReason() { return revokeReason; }
    public void setRevokeReason(String revokeReason) { this.revokeReason = revokeReason; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
}
