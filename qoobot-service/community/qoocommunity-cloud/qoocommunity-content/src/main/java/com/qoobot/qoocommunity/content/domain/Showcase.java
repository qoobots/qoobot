package com.qoobot.qoocommunity.content.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@Entity
@Table(name = "content_showcases")
@EqualsAndHashCode(callSuper = true)
public class Showcase extends com.qoobot.qoocommunity.common.entity.BaseEntity {

    @Column(nullable = false, length = 500)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "content_html", columnDefinition = "TEXT")
    private String contentHtml;

    @Column(name = "cover_url", length = 512)
    private String coverUrl;

    @Column(name = "video_url", length = 512)
    private String videoUrl;

    @Column(name = "project_url", length = 512)
    private String projectUrl;

    @Column(name = "author_id", nullable = false, length = 64)
    private String authorId;

    @Column(length = 50)
    private String category;

    @Column(columnDefinition = "varchar(50)[]")
    private String tags;

    @Column(name = "is_featured")
    private Boolean isFeatured = false;

    @Column(name = "like_count")
    private Integer likeCount = 0;

    @Column(name = "view_count")
    private Integer viewCount = 0;

    @Column(length = 20)
    private String status = "PENDING";
}
