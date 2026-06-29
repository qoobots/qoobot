package com.qoobot.qoocommunity.academy.domain;

import com.qoobot.qoocommunity.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@Entity
@Table(name = "academy_learning_paths")
@EqualsAndHashCode(callSuper = true)
public class LearningPath extends BaseEntity {

    @Column(nullable = false, length = 200)
    private String title;

    @Column(length = 100)
    private String slug;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "cover_url", length = 512)
    private String coverUrl;

    @Column(length = 20)
    private String level;

    @Column(name = "course_count")
    private Integer courseCount = 0;

    @Column(name = "sort_order")
    private Integer sortOrder = 0;

    @Column(name = "is_published")
    private Boolean isPublished = false;
}
