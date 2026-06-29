package com.qoobot.qooauth.security.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * Security event entity for threat detection and incident response.
 * Records anomalous events with severity classification.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "security_events")
public class SecurityEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * User associated with the event (nullable for anonymous threats).
     */
    @Column(name = "user_id", length = 32)
    private String userId;

    /**
     * Type of security event (e.g., "LOGIN_ANOMALY", "CREDENTIAL_STUFFING",
     * "DEVICE_SPOOFING", "JAILBREAK_DETECTED", "INTEGRITY_FAILURE",
     * "RATE_LIMIT_BREACH", "GEO_ANOMALY").
     */
    @Column(name = "event_type", nullable = false, length = 64)
    private String eventType;

    /**
     * Severity level: "LOW", "MEDIUM", "HIGH", "CRITICAL".
     */
    @Column(name = "severity", nullable = false, length = 16)
    private String severity;

    /**
     * Source IP address of the event.
     */
    @Column(name = "source_ip", length = 45)
    private String sourceIp;

    /**
     * Additional event details stored as JSONB.
     */
    @Column(name = "details", columnDefinition = "jsonb")
    private String details;

    /**
     * Timestamp when the event was detected.
     */
    @Column(name = "detected_at", nullable = false)
    @Builder.Default
    private Instant detectedAt = Instant.now();

    /**
     * Timestamp when the event was resolved (null if unresolved).
     */
    @Column(name = "resolved_at")
    private Instant resolvedAt;

    @PrePersist
    protected void onCreate() {
        if (detectedAt == null) {
            detectedAt = Instant.now();
        }
    }
}
