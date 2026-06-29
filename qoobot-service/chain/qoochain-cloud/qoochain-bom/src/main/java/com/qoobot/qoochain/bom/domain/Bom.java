package com.qoobot.qoochain.bom.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDate;

@Entity
@Table(name = "bom")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class Bom extends BaseEntity {

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    @Column(nullable = false, length = 16)
    private String version;

    @Column(name = "bom_type", nullable = false, length = 8)
    @Enumerated(EnumType.STRING)
    private BomType bomType;

    @Column(nullable = false, length = 16)
    @Enumerated(EnumType.STRING)
    private BomStatus status = BomStatus.DRAFT;

    @Column(name = "total_items", nullable = false)
    private int totalItems = 0;

    @Column(name = "estimated_cost", precision = 12, scale = 2)
    private BigDecimal estimatedCost;

    @Column(name = "cost_currency", length = 3)
    private String costCurrency = "CNY";

    @Column(name = "released_at")
    private LocalDate releasedAt;

    @Column(name = "created_by", nullable = false, length = 64)
    private String createdBy;

    public enum BomType { EBOM, MBOM }
    public enum BomStatus { DRAFT, UNDER_REVIEW, RELEASED, FROZEN }
}
