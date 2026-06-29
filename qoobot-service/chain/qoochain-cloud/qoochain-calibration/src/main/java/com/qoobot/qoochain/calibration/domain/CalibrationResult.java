package com.qoobot.qoochain.calibration.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;

@Entity
@Table(name = "calibration_result")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class CalibrationResult extends BaseEntity {
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "session_id", nullable = false)
    private CalibrationSession session;
    @Column(name = "sensor_type", nullable = false, length = 32)
    private String sensorType;
    @Column(name = "parameter_name", nullable = false, length = 64)
    private String parameterName;
    @Column(name = "parameter_value", nullable = false, precision = 16, scale = 8)
    private BigDecimal parameterValue;
    @Column(length = 16)
    private String unit;
    @Column(name = "accuracy_metric", length = 64)
    private String accuracyMetric;
    @Column(name = "accuracy_value", precision = 16, scale = 8)
    private BigDecimal accuracyValue;
    @Column(name = "accuracy_unit", length = 16)
    private String accuracyUnit;
    @Column(name = "spec_lower", precision = 16, scale = 8)
    private BigDecimal specLower;
    @Column(name = "spec_upper", precision = 16, scale = 8)
    private BigDecimal specUpper;
    @Column(nullable = false)
    private boolean passed;
    @Column(name = "raw_data_url", length = 512)
    private String rawDataUrl;
}
