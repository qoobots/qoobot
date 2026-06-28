package com.qoobot.qoocommunity.academy.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@Entity
@Table(name = "academy_lessons")
@EqualsAndHashCode(callSuper = true)
public class Lesson extends com.qoobot.qoocommunity.common.entity.BaseEntity {

    @Column(name = "course_id", nullable = false)
    private Long courseId;

    @Column(nullable = false, length = 500)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String content;

    @Column(name = "content_html", columnDefinition = "TEXT")
    private String contentHtml;

    @Column(name = "video_url", length = 512)
    private String videoUrl;

    @Column(name = "duration_minutes")
    private Integer durationMinutes = 0;

    @Column(name = "sort_order")
    private Integer sortOrder = 0;

    @Column(name = "is_free")
    private Boolean isFree = true;
}
