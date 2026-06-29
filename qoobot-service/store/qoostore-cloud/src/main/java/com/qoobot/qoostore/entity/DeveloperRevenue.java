package com.qoobot.qoostore.entity;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "developer_revenue")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DeveloperRevenue {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "developer_id", nullable = false)
    private Long developerId;

    @Column(name = "order_id", nullable = false)
    private Long orderId;

    @Column(name = "skill_id", nullable = false)
    private Long skillId;

    @Column(name = "gross_amount", nullable = false, precision = 10, scale = 2)
    private BigDecimal grossAmount;

    @Column(name = "platform_fee", nullable = false, precision = 10, scale = 2)
    private BigDecimal platformFee;

    @Column(name = "developer_share", nullable = false, precision = 10, scale = 2)
    private BigDecimal developerShare;

    @Column(name = "share_rate", nullable = false, precision = 5, scale = 4)
    private BigDecimal shareRate;

    @Column(length = 3)
    @Builder.Default
    private String currency = "USD";

    @Column(name = "created_at")
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();
}
