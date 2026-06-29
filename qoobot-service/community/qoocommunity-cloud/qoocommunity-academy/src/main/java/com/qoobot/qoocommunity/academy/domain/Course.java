package com.qoobot.qoocommunity.academy.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@Entity
@Table(name = "academy_courses")
@EqualsAndHashCode(callSuper = true)
public class Course extends com.qoobot.qoocommunity.common.entity.BaseEntity {

    @Column(nullable = false, length = 500)
    private String title;

    @Column(nullable = false, unique = true, length = 200)
    private String slug;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "cover_url", length = 512)
    private String coverUrl;

    @Column(nullable = false, length = 20)
    private String level;

    @Column(length = 50)
    private String category;

    @Column(name = "lesson_count")
    private Integer lessonCount = 0;

    @Column(name = "enrolled_count")
    private Integer enrolledCount = 0;

    @Column(name = "duration_minutes")
    private Integer durationMinutes = 0;

    @Column(name = "is_published")
    private Boolean isPublished = false;
}
