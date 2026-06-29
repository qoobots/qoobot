package com.qoobot.qoochain.bom.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import java.time.Instant;

@Entity
@Table(name = "material_alternative")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class MaterialAlternative extends BaseEntity {

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "material_id", nullable = false)
    private Material material;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "alternative_id", nullable = false)
    private Material alternative;

    @Column(nullable = false, length = 16)
    @Enumerated(EnumType.STRING)
    private Compatibility compatibility;

    @Column(nullable = false)
    private boolean verified = false;

    @Column(name = "verified_at")
    private Instant verifiedAt;

    @Column(columnDefinition = "TEXT")
    private String notes;

    public enum Compatibility {
        DROP_IN, FORM_FIT, MINOR_MOD, MAJOR_MOD
    }
}
