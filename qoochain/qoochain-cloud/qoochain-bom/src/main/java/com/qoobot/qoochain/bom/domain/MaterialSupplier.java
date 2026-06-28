package com.qoobot.qoochain.bom.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDate;

@Entity
@Table(name = "material_supplier")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class MaterialSupplier extends BaseEntity {

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "material_id", nullable = false)
    private Material material;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "supplier_id", nullable = false)
    private Supplier supplier;

    @Column(name = "supplier_pn", length = 64)
    private String supplierPn;

    @Column(name = "unit_price", precision = 10, scale = 2)
    private BigDecimal unitPrice;

    @Column(length = 3)
    private String currency = "CNY";

    @Column(name = "is_preferred")
    private boolean isPreferred = false;

    @Column(name = "qualification_status", length = 16)
    private String qualificationStatus = "QUALIFIED";

    @Column(name = "qualified_at")
    private LocalDate qualifiedAt;
}
