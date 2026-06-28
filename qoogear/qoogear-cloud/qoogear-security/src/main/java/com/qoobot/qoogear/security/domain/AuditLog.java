package com.qoobot.qoogear.security.domain;

import com.qoobot.qoogear.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.time.ZonedDateTime;

@Data
@Entity
@Table(name = "audit_logs")
@EqualsAndHashCode(callSuper = true)
public class AuditLog extends BaseEntity {

    @Column(nullable = false, length = 100)
    private String actor;

    @Column(name = "actor_type", nullable = false, length = 20)
    private String actorType;

    @Column(nullable = false, length = 50)
    private String action;

    @Column(name = "resource_type", nullable = false, length = 50)
    private String resourceType;

    @Column(name = "resource_id")
    private Long resourceId;

    @Column(name = "details_json", columnDefinition = "JSONB")
    private String detailsJson;

    @Column(name = "ip_address", length = 45)
    private String ipAddress;

    @Column(name = "created_at", nullable = false, updatable = false)
    private ZonedDateTime created;
}
