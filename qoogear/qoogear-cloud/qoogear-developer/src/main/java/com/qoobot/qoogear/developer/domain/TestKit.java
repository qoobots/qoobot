package com.qoobot.qoogear.developer.domain;

import com.qoobot.qoogear.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.math.BigDecimal;
import java.util.List;

@Data
@Entity
@Table(name = "test_kits")
@EqualsAndHashCode(callSuper = true)
public class TestKit extends BaseEntity {

    @Column(nullable = false, length = 200)
    private String name;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "kit_type", nullable = false, length = 50)
    private String kitType;

    @Column(precision = 10, scale = 2)
    private BigDecimal price;

    @Column(length = 10)
    private String currency = "CNY";

    @Column
    private Integer stock = 0;

    @Column(name = "compatible_standards", columnDefinition = "bigint[]")
    private List<Long> compatibleStandards;

    @Column(name = "image_url", length = 500)
    private String imageUrl;

    @Column(name = "is_available")
    private Boolean isAvailable = true;
}
