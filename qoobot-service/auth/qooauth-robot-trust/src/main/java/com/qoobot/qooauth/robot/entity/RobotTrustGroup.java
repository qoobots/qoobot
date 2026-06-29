package com.qoobot.qooauth.robot.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.Map;

@Entity
@Table(name = "robot_trust_groups", indexes = {
    @Index(name = "idx_rtg_owner_device_id", columnList = "owner_device_id"),
    @Index(name = "idx_rtg_state", columnList = "state")
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RobotTrustGroup {

    @Id
    @Column(name = "group_id", length = 32, nullable = false)
    private String groupId;

    @Column(name = "name", length = 128, nullable = false)
    private String name;

    @Column(name = "owner_device_id", length = 32, nullable = false)
    private String ownerDeviceId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "trust_policy", columnDefinition = "jsonb")
    private Map<String, Object> trustPolicy;

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
