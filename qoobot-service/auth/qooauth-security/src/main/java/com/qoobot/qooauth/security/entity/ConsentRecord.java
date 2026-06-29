package com.qoobot.qooauth.security.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * User consent record for GDPR/CCPA/PIPL compliance.
 * Tracks informed consent lifecycle: grant, withdrawal, and versioning.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "consent_records")
public class ConsentRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * The user who provided or revoked consent.
     */
    @Column(name = "user_id", nullable = false, length = 32)
    private String userId;

    /**
     * Type of consent (e.g., "DATA_COLLECTION", "MARKETING", "THIRD_PARTY_SHARING",
     * "COOKIES", "ANALYTICS", "BIOMETRIC").
     */
    @Column(name = "consent_type", nullable = false, length = 64)
    private String consentType;

    /**
     * Version of the consent policy at the time of action.
     */
    @Column(name = "version", nullable = false, length = 16)
    private String version;

    /**
     * Whether consent is currently granted.
     */
    @Column(name = "granted", nullable = false)
    private Boolean granted;

    /**
     * Timestamp when consent was granted.
     */
    @Column(name = "granted_at")
    private Instant grantedAt;

    /**
     * Timestamp when consent was revoked (null if still active).
     */
    @Column(name = "revoked_at")
    private Instant revokedAt;

    /**
     * IP address from which the consent action was performed.
     */
    @Column(name = "ip_address", length = 45)
    private String ipAddress;

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();

    @PrePersist
    protected void onCreate() {
        if (createdAt == null) {
            createdAt = Instant.now();
        }
    }
}
