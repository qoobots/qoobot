package com.qoobot.qoochain.bom.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "material")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class Material extends BaseEntity {

    @Column(name = "material_code", nullable = false, unique = true, length = 64)
    private String materialCode;

    @Column(name = "material_name", nullable = false, length = 128)
    private String materialName;

    @Column(nullable = false, length = 32)
    private String category;

    @Column(columnDefinition = "TEXT")
    private String specification;

    @Column(length = 128)
    private String manufacturer;

    @Column(name = "manufacturer_pn", length = 64)
    private String manufacturerPn;

    @Column(nullable = false, length = 16)
    @Enumerated(EnumType.STRING)
    private Lifecycle lifecycle = Lifecycle.ACTIVE;

    @Column(name = "lead_time_days")
    private Integer leadTimeDays;

    @Column(name = "moq")
    private Integer moq;

    @Column(name = "rohs_compliant")
    private boolean rohsCompliant = false;

    @Column(name = "reach_compliant")
    private boolean reachCompliant = false;

    public enum Lifecycle { ACTIVE, NRND, EOL, OBSOLETE }
}
