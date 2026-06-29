package com.qoobot.qooauth.developer.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.List;

@Entity
@Table(name = "developer_certificates", indexes = {
    @Index(name = "idx_dc_user_id", columnList = "user_id"),
    @Index(name = "idx_dc_serial_number", columnList = "serial_number", unique = true),
    @Index(name = "idx_dc_state", columnList = "state"),
    @Index(name = "idx_dc_team_id", columnList = "team_id")
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DeveloperCertificate {

    @Id
    @Column(name = "cert_id", length = 32, nullable = false)
    private String certId;

    @Column(name = "user_id", length = 32, nullable = false)
    private String userId;

    @Column(name = "cert_type", length = 32, nullable = false)
    private String certType;

    @Column(name = "team_id", length = 32)
    private String teamId;

    @Column(name = "serial_number", length = 64, nullable = false, unique = true)
    private String serialNumber;

    @Column(name = "sha256_fingerprint", length = 64, nullable = false)
    private String sha256Fingerprint;

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    @Column(name = "state", length = 32, nullable = false)
    @Builder.Default
    private String state = "ACTIVE";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "capabilities", columnDefinition = "jsonb")
    private List<String> capabilities;

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();

    @Column(name = "revoked_at")
    private Instant revokedAt;

    @PrePersist
    protected void onCreate() {
        if (createdAt == null) {
            createdAt = Instant.now();
        }
        if (state == null) {
            state = "ACTIVE";
        }
    }
}
