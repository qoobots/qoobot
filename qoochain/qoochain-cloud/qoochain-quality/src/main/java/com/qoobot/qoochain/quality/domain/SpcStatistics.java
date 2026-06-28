package com.qoobot.qoochain.quality.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "spc_statistics")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class SpcStatistics extends BaseEntity {
    @Column(name = "measurement_name", nullable = false, length = 64)
    private String measurementName;
    @Column(name = "station_code", length = 64)
    private String stationCode;
    @Column(name = "period_start", nullable = false)
    private Instant periodStart;
    @Column(name = "period_end", nullable = false)
    private Instant periodEnd;
    @Column(name = "sample_count", nullable = false)
    private int sampleCount;
    @Column(name = "mean_value", precision = 12, scale = 4)
    private BigDecimal meanValue;
    @Column(name = "std_dev", precision = 12, scale = 4)
    private BigDecimal stdDev;
    @Column(precision = 8, scale = 4)
    private BigDecimal cp;
    @Column(precision = 8, scale = 4)
    private BigDecimal cpk;
    @Column(precision = 12, scale = 4)
    private BigDecimal ucl;
    @Column(precision = 12, scale = 4)
    private BigDecimal lcl;
    @Column(name = "out_of_control")
    private boolean outOfControl = false;
}
