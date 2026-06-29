package com.qoobot.qoochain.aftermarket.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "spare_part")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class SparePart extends BaseEntity {
    @Column(name = "material_id", nullable = false)
    private Long materialId;
    @Column(name = "warehouse_code", nullable = false, length = 64)
    private String warehouseCode;
    @Column(name = "stock_quantity", nullable = false)
    private int stockQuantity = 0;
    @Column(name = "safety_stock", nullable = false)
    private int safetyStock = 0;
    @Column(name = "reorder_point", nullable = false)
    private int reorderPoint = 0;
}
