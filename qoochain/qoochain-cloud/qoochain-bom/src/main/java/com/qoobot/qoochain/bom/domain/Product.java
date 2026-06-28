package com.qoobot.qoochain.bom.domain;

import com.qoobot.qoochain.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "product")
@Data @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class Product extends BaseEntity {

    @Column(name = "model_code", nullable = false, unique = true, length = 64)
    private String modelCode;

    @Column(name = "model_name", nullable = false, length = 128)
    private String modelName;

    @Column(nullable = false, length = 32)
    private String category;

    @Column(nullable = false, length = 16)
    @Enumerated(EnumType.STRING)
    private ProductStatus status = ProductStatus.DRAFT;

    public enum ProductStatus {
        DRAFT, RELEASED, OBSOLETE
    }
}
