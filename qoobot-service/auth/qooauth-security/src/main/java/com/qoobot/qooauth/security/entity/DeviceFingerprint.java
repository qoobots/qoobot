package com.qoobot.qooauth.security.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * Device fingerprint entity for browser/device identification.
 * Stores Canvas/WebGL/Font hashing results and risk scoring.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "device_fingerprints")
public class DeviceFingerprint {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * Associated user ID (nullable for anonymous fingerprints).
     */
    @Column(name = "user_id", length = 32)
    private String userId;

    /**
     * Composite fingerprint hash (SHA-256 of Canvas + WebGL + Font + Navigator data).
     */
    @Column(name = "fingerprint_hash", nullable = false, length = 64)
    private String fingerprintHash;

    /**
     * Raw fingerprint components stored as JSONB:
     * { canvas: "...", webgl: "...", fonts: [...], navigator: {...}, screen: {...} }.
     */
    @Column(name = "components", columnDefinition = "jsonb")
    private String components;

    /**
     * Computed risk score (0.0 = safe, 1.0 = high risk).
     */
    @Column(name = "risk_score")
    private Double riskScore;

    /**
     * Whether this fingerprint is associated with a known legitimate device.
     */
    @Column(name = "is_known", nullable = false)
    @Builder.Default
    private Boolean isKnown = false;

    /**
     * Timestamp when this fingerprint was first observed.
     */
    @Column(name = "first_seen_at", nullable = false)
    @Builder.Default
    private Instant firstSeenAt = Instant.now();

    /**
     * Timestamp when this fingerprint was last observed.
     */
    @Column(name = "last_seen_at", nullable = false)
    @Builder.Default
    private Instant lastSeenAt = Instant.now();

    @PrePersist
    protected void onCreate() {
        Instant now = Instant.now();
        if (firstSeenAt == null) {
            firstSeenAt = now;
        }
        if (lastSeenAt == null) {
            lastSeenAt = now;
        }
    }
}
