package com.qoobot.qoochain.line.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "station")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class Station extends BaseEntity {
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "line_id", nullable = false)
    private ProductionLine line;
    @Column(name = "station_code", nullable = false, length = 64)
    private String stationCode;
    @Column(name = "station_name", nullable = false, length = 128)
    private String stationName;
    @Column(nullable = false)
    private int sequence;
    @Column(name = "cycle_time_min", nullable = false)
    private int cycleTimeMin;
    @Column(name = "tools_required", columnDefinition = "TEXT")
    private String toolsRequired;
    @Column(name = "poka_yoke_rules", columnDefinition = "TEXT")
    private String pokaYokeRules;
}
