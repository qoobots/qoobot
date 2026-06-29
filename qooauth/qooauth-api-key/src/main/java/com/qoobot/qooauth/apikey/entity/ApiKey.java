package com.qoobot.qooauth.apikey.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.List;

@Entity
@Table(name = "api_keys", indexes = {
    @Index(name = "idx_api_keys_user_id", columnList = "user_id"),
    @Index(name = "idx_api_keys_key_prefix", columnList = "key_prefix", unique = true),
    @Index(name = "idx_api_keys_state", columnList = "state")
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ApiKey {

    @Id
    @Column(name = "key_id", length = 32, nullable = false)
    private String keyId;

    @Column(name = "user_id", length = 32, nullable = false)
    private String userId;

    @Column(name = "key_prefix", length = 12, nullable = false, unique = true)
    private String keyPrefix;

    @Column(name = "key_hash", length = 255, nullable = false)
    private String keyHash;

    @Column(name = "name", length = 128)
    private String name;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "permissions", columnDefinition = "jsonb")
    private List<String> permissions;

    @Column(name = "state", length = 32, nullable = false)
    @Builder.Default
    private String state = "ACTIVE";

    @Column(name = "expires_at")
    private Instant expiresAt;

    @Column(name = "last_used_at")
    private Instant lastUsedAt;

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
