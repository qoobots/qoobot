package com.qoobot.qooauth.robot.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.List;

@Entity
@Table(name = "collaboration_tokens", indexes = {
    @Index(name = "idx_ct_issuer_device_id", columnList = "issuer_device_id"),
    @Index(name = "idx_ct_recipient_device_id", columnList = "recipient_device_id"),
    @Index(name = "idx_ct_state", columnList = "state"),
    @Index(name = "idx_ct_expires_at", columnList = "expires_at")
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CollaborationToken {

    @Id
    @Column(name = "token_id", length = 32, nullable = false)
    private String tokenId;

    @Column(name = "issuer_device_id", length = 32, nullable = false)
    private String issuerDeviceId;

    @Column(name = "recipient_device_id", length = 32, nullable = false)
    private String recipientDeviceId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "capabilities", columnDefinition = "jsonb")
    private List<String> capabilities;

    @Column(name = "token_hash", length = 255, nullable = false)
    private String tokenHash;

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    @Column(name = "state", length = 32, nullable = false)
    @Builder.Default
    private String state = "ACTIVE";

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();

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
