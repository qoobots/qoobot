package com.qoobot.qoocommunity.academy.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@Entity
@Table(name = "academy_certifications")
@EqualsAndHashCode(callSuper = true)
public class Certification extends com.qoobot.qoocommunity.common.entity.BaseEntity {

    @Column(nullable = false, length = 200)
    private String name;

    @Column(nullable = false, unique = true, length = 100)
    private String slug;

    @Column(nullable = false, length = 20)
    private String level;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "exam_duration")
    private Integer examDuration = 60;

    @Column(name = "pass_score")
    private Integer passScore = 70;

    @Column(name = "question_count")
    private Integer questionCount = 50;

    @Column(name = "validity_months")
    private Integer validityMonths = 24;

    @Column(name = "is_active")
    private Boolean isActive = true;
}
