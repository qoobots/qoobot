package com.qoobot.qoocommunity.contributor.domain;

import com.qoobot.qoocommunity.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "cla_records")
@EqualsAndHashCode(callSuper = true)
public class ClaRecord extends BaseEntity {

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    @Column(name = "cla_version", length = 20)
    private String claVersion;

    @Column(name = "cla_type", length = 20)
    private String claType;

    @Column(name = "signed_at")
    private LocalDateTime signedAt;

    @Column(name = "ip_address", length = 45)
    private String ipAddress;

    @Column(name = "user_agent", length = 512)
    private String userAgent;
}
