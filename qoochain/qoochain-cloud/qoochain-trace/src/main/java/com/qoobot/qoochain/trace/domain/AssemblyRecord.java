package com.qoobot.qoochain.trace.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import java.time.Instant;

@Entity
@Table(name = "assembly_record")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class AssemblyRecord extends BaseEntity {
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "robot_id", nullable = false)
    private Robot robot;
    @Column(name = "station_id", nullable = false)
    private Long stationId;
    @Column(name = "operator_id", nullable = false, length = 64)
    private String operatorId;
    @Column(name = "started_at", nullable = false)
    private Instant startedAt;
    @Column(name = "completed_at")
    private Instant completedAt;
    @Column(nullable = false, length = 16)
    private String status = "IN_PROGRESS";
    @Column(name = "torque_curve_url", length = 512)
    private String torqueCurveUrl;
    @Column(columnDefinition = "TEXT")
    private String notes;
}
