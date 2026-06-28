package com.qoobot.qoogear.standard.domain;

import com.qoobot.qoogear.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@Entity
@Table(name = "test_checklist")
@EqualsAndHashCode(callSuper = true)
public class TestChecklist extends BaseEntity {

    @Column(name = "standard_id", nullable = false)
    private Long standardId;

    @Column(name = "test_item", nullable = false, length = 200)
    private String testItem;

    @Column(name = "test_method", columnDefinition = "TEXT")
    private String testMethod;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String criteria;

    @Column(nullable = false)
    private Boolean required = true;

    @Column(name = "sort_order")
    private Integer sortOrder = 0;
}
