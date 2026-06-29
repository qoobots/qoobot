package com.qoobot.qoogear.cert.domain;

import com.qoobot.qoogear.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.time.ZonedDateTime;

@Data
@Entity
@Table(name = "auth_chips")
@EqualsAndHashCode(callSuper = true)
public class AuthChip extends BaseEntity {

    @Column(name = "certificate_id", nullable = false)
    private Long certificateId;

    @Column(name = "chip_id", nullable = false, unique = true, length = 100)
    private String chipId;

    @Column(name = "chip_type", nullable = false, length = 50)
    private String chipType;

    @Column(name = "batch_number", nullable = false, length = 100)
    private String batchNumber;

    @Column(name = "burned_at", nullable = false)
    private ZonedDateTime burnedAt;

    @Column(length = 20)
    private String status = "active";
}
