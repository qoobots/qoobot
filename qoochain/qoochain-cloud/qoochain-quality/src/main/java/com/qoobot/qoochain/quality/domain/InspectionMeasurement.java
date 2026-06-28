package com.qoobot.qoochain.quality.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;

@Entity
@Table(name = "inspection_measurement")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class InspectionMeasurement extends BaseEntity {
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "inspection_id", nullable = false)
    private InspectionRecord inspection;
    @Column(name = "measurement_name", nullable = false, length = 64)
    private String measurementName;
    @Column(nullable = false, precision = 12, scale = 4)
    private BigDecimal value;
    @Column(length = 16)
    private String unit;
    @Column(name = "spec_lower", precision = 12, scale = 4)
    private BigDecimal specLower;
    @Column(name = "spec_upper", precision = 12, scale = 4)
    private BigDecimal specUpper;
    @Column(nullable = false, length = 8)
    private String result; // PASS, FAIL
}
