package com.qoobot.qoochain.quality.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import java.time.Instant;

@Entity
@Table(name = "inspection_record")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class InspectionRecord extends BaseEntity {
    @Column(name = "robot_id")
    private Long robotId;
    @Column(name = "material_id")
    private Long materialId;
    @Column(name = "inspection_type", nullable = false, length = 8)
    private String inspectionType; // IQC, IPQC, OQC
    @Column(name = "station_code", length = 64)
    private String stationCode;
    @Column(name = "inspector_id", nullable = false, length = 64)
    private String inspectorId;
    @Column(name = "lot_number", length = 64)
    private String lotNumber;
    @Column(name = "sample_size")
    private int sampleSize;
    @Column(name = "defect_count")
    private int defectCount = 0;
    @Column(name = "overall_result", nullable = false, length = 10)
    private String overallResult; // PASS, FAIL, CONCESSION
    @Column(columnDefinition = "TEXT")
    private String notes;
    @Column(name = "inspected_at", nullable = false)
    private Instant inspectedAt = Instant.now();
}
