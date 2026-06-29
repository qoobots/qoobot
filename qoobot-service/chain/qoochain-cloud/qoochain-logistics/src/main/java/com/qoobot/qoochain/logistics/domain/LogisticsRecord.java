package com.qoobot.qoochain.logistics.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDate;
import java.time.Instant;

@Entity
@Table(name = "logistics_record")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class LogisticsRecord extends BaseEntity {
    @Column(name = "robot_id", nullable = false)
    private Long robotId;
    @Column(name = "tracking_number", length = 128)
    private String trackingNumber;
    @Column(length = 64)
    private String carrier;
    @Column(name = "from_location", length = 128)
    private String fromLocation;
    @Column(name = "to_location", length = 128)
    private String toLocation;
    @Column(nullable = false, length = 16)
    private String status; // PICKED, PACKED, SHIPPED, IN_TRANSIT, DELIVERED
    @Column(name = "status_updated_at")
    private Instant statusUpdatedAt = Instant.now();
    @Column(name = "estimated_delivery")
    private LocalDate estimatedDelivery;
    @Column(name = "actual_delivery")
    private LocalDate actualDelivery;
}
