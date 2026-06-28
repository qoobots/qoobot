package com.qoobot.qoogear.security.domain;

import com.qoobot.qoogear.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.time.ZonedDateTime;

@Data
@Entity
@Table(name = "security_audits")
@EqualsAndHashCode(callSuper = true)
public class SecurityAudit extends BaseEntity {

    @Column(name = "application_id", nullable = false)
    private Long applicationId;

    @Column(name = "risk_level", nullable = false, length = 20)
    private String riskLevel;

    @Column(name = "fmea_json", columnDefinition = "JSONB")
    private String fmeaJson;

    @Column(name = "auditor_id", nullable = false)
    private Long auditorId;

    @Column(columnDefinition = "TEXT")
    private String findings;

    @Column(columnDefinition = "TEXT")
    private String recommendation;

    @Column(nullable = false, length = 20)
    private String status = "pending";

    @Column(name = "completed_at")
    private ZonedDateTime completedAt;
}
