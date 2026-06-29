package com.qoobot.qoogear.standard.domain;

import com.qoobot.qoogear.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@Entity
@Table(name = "compatibility_matrix")
@EqualsAndHashCode(callSuper = true)
public class CompatibilityMatrix extends BaseEntity {

    @Column(name = "spec_id_a", nullable = false)
    private Long specIdA;

    @Column(name = "spec_version_a", nullable = false, length = 20)
    private String specVersionA;

    @Column(name = "spec_id_b", nullable = false)
    private Long specIdB;

    @Column(name = "spec_version_b", nullable = false, length = 20)
    private String specVersionB;

    @Column(nullable = false, length = 20)
    private String compatibility;

    @Column(name = "condition_desc", columnDefinition = "TEXT")
    private String conditionDesc;
}
