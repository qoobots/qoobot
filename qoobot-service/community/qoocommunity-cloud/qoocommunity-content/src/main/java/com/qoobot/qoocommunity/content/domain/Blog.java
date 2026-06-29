package com.qoobot.qoocommunity.content.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "content_blogs")
@EqualsAndHashCode(callSuper = true)
public class Blog extends com.qoobot.qoocommunity.common.entity.BaseEntity {

    @Column(nullable = false, length = 500)
    private String title;

    @Column(nullable = false, unique = true, length = 200)
    private String slug;

    @Column(columnDefinition = "TEXT")
    private String summary;

    @Column(columnDefinition = "TEXT", nullable = false)
    private String content;

    @Column(name = "content_html", columnDefinition = "TEXT", nullable = false)
    private String contentHtml;

    @Column(name = "cover_url", length = 512)
    private String coverUrl;

    @Column(name = "author_id", nullable = false, length = 64)
    private String authorId;

    @Column(columnDefinition = "varchar(50)[]")
    private String tags;

    @Column(name = "is_published")
    private Boolean isPublished = false;

    @Column(name = "published_at")
    private LocalDateTime publishedAt;

    @Column(name = "view_count")
    private Integer viewCount = 0;
}
