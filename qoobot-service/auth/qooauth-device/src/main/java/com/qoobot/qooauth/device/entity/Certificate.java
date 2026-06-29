package com.qoobot.qooauth.device.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.OffsetDateTime;

/**
 * JPA entity mapping to the {@code certificates} table.
 * <p>
 * Tracks every X.509 certificate issued by the device CA, including
 * its type (DEVICE / CA / SERVICE), subject, validity period, and
 * revocation state.
 */
@Entity
@Table(name = "certificates")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@ToString(onlyExplicitlyIncluded = true)
public class Certificate {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false, updatable = false)
    private Long id;

    @Column(name = "serial_number", length = 64, nullable = false, unique = true)
    @ToString.Include
    private String serialNumber;

    @Column(name = "cert_type", length = 32, nullable = false)
    private String certType;

    @Column(name = "subject_cn", length = 256, nullable = false)
    private String subjectCn;

    @Column(name = "subject_org", length = 128)
    private String subjectOrg;

    @Column(name = "device_id", length = 32)
    @ToString.Include
    private String deviceId;

    @Column(name = "not_before", nullable = false)
    private OffsetDateTime notBefore;

    @Column(name = "not_after", nullable = false)
    private OffsetDateTime notAfter;

    @Column(name = "state", length = 32, nullable = false)
    @Builder.Default
    private String state = "ACTIVE";

    @Column(name = "revoked_at")
    private OffsetDateTime revokedAt;

    @Column(name = "revocation_reason", length = 256)
    private String revocationReason;

    @Column(name = "sha256_fingerprint", length = 64, nullable = false, unique = true)
    private String sha256Fingerprint;

    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    // --- Lifecycle callbacks ---

    @PrePersist
    protected void onCreate() {
        if (createdAt == null) {
            createdAt = OffsetDateTime.now();
        }
    }

    // --- Convenience helpers ---

    public boolean isActive() {
        return "ACTIVE".equals(state);
    }

    public boolean isRevoked() {
        return "REVOKED".equals(state);
    }

    public boolean isExpired() {
        return "EXPIRED".equals(state);
    }

    public boolean isValid() {
        OffsetDateTime now = OffsetDateTime.now();
        return isActive() && notBefore != null && notAfter != null
                && !now.isBefore(notBefore) && !now.isAfter(notAfter);
    }

    // --- Constants ---

    public static final String CERT_TYPE_DEVICE = "DEVICE";
    public static final String CERT_TYPE_CA = "CA";
    public static final String CERT_TYPE_SERVICE = "SERVICE";

    public static final String STATE_ACTIVE = "ACTIVE";
    public static final String STATE_REVOKED = "REVOKED";
    public static final String STATE_EXPIRED = "EXPIRED";
}
