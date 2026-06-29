package com.qoobot.qoochain.trace.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import java.time.Instant;

@Entity
@Table(name = "component_trace")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class ComponentTrace extends BaseEntity {
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "robot_id", nullable = false)
    private Robot robot;
    @Column(name = "material_id", nullable = false)
    private Long materialId;
    @Column(name = "lot_number", nullable = false, length = 64)
    private String lotNumber;
    @Column(name = "supplier_id")
    private Long supplierId;
    @Column(nullable = false)
    private int quantity = 1;
    @Column(name = "installed_at", nullable = false)
    private Instant installedAt = Instant.now();
}
