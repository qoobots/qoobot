package com.qoobot.qoochain.line.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "sop_step")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class SopStep extends BaseEntity {
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "station_id", nullable = false)
    private Station station;
    @Column(name = "step_number", nullable = false)
    private int stepNumber;
    @Column(nullable = false, columnDefinition = "TEXT")
    private String description;
    @Column(name = "duration_min", nullable = false)
    private int durationMin;
    @Column(length = 256)
    private String tools;
    @Column(name = "torque_spec", precision = 8, scale = 2)
    private java.math.BigDecimal torqueSpec;
    @Column(name = "inspection_point")
    private boolean inspectionPoint = false;
    @Column(name = "image_url", length = 512)
    private String imageUrl;
}
