package com.qoobot.qoocommunity.forum.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "forum_categories")
@EqualsAndHashCode(callSuper = true)
public class Category extends com.qoobot.qoocommunity.common.entity.BaseEntity {

    @Column(nullable = false, length = 100)
    private String name;

    @Column(nullable = false, unique = true, length = 100)
    private String slug;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "sort_order")
    private Integer sortOrder = 0;

    @Column(name = "parent_id")
    private Long parentId;

    @Column(name = "topic_count")
    private Integer topicCount = 0;
}
