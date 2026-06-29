package com.qoobot.qoochain.trace.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDate;
import java.time.Instant;

@Entity
@Table(name = "robot")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class Robot extends BaseEntity {
    @Column(name = "serial_number", nullable = false, unique = true, length = 64)
    private String serialNumber;
    @Column(name = "product_id", nullable = false)
    private Long productId;
    @Column(name = "hardware_version", nullable = false, length = 16)
    private String hardwareVersion;
    @Column(name = "firmware_version", length = 16)
    private String firmwareVersion;
    @Column(name = "production_line_id")
    private Long productionLineId;
    @Column(nullable = false, length = 16)
    @Enumerated(EnumType.STRING)
    private RobotStatus status = RobotStatus.MANUFACTURING;
    @Column(name = "manufactured_at")
    private LocalDate manufacturedAt;
    @Column(name = "shipped_at")
    private Instant shippedAt;

    public enum RobotStatus { MANUFACTURING, CALIBRATING, TESTING, FINISHED, SHIPPED }
}
