package com.qoobot.qooauth.developer.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;

@Entity
@Table(name = "skill_signatures", indexes = {
    @Index(name = "idx_ss_developer_id", columnList = "developer_id"),
    @Index(name = "idx_ss_skill_hash", columnList = "skill_hash")
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SkillSignature {

    @Id
    @Column(name = "sig_id", length = 32, nullable = false)
    private String sigId;

    @Column(name = "developer_id", length = 32, nullable = false)
    private String developerId;

    @Column(name = "skill_hash", length = 64, nullable = false)
    private String skillHash;

    @Column(name = "signature", length = 512, nullable = false)
    private String signature;

    @Column(name = "verified", nullable = false)
    @Builder.Default
    private Boolean verified = false;

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();

    @PrePersist
    protected void onCreate() {
        if (createdAt == null) {
            createdAt = Instant.now();
        }
        if (verified == null) {
            verified = false;
        }
    }
}
