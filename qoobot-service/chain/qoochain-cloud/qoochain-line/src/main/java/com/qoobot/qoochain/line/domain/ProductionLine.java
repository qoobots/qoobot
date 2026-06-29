package com.qoobot.qoochain.line.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "production_line")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class ProductionLine extends BaseEntity {
    @Column(name = "line_code", nullable = false, unique = true, length = 64)
    private String lineCode;
    @Column(name = "line_name", nullable = false, length = 128)
    private String lineName;
    @Column(length = 128)
    private String location;
    @Column(name = "product_model", nullable = false, length = 64)
    private String productModel;
    @Column(nullable = false, length = 16)
    @Enumerated(EnumType.STRING)
    private LineStatus status = LineStatus.ACTIVE;
    @Column(name = "takt_time_min")
    private Integer taktTimeMin;
    @Column(name = "daily_capacity")
    private Integer dailyCapacity;

    public enum LineStatus { ACTIVE, INACTIVE, MAINTENANCE }
}
