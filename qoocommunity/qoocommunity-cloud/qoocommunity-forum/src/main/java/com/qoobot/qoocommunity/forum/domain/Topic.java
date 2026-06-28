package com.qoobot.qoocommunity.forum.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "forum_topics")
@EqualsAndHashCode(callSuper = true)
public class Topic extends com.qoobot.qoocommunity.common.entity.BaseEntity {

    @Column(name = "category_id", nullable = false)
    private Long categoryId;

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    @Column(nullable = false, length = 500)
    private String title;

    @Column(columnDefinition = "TEXT", nullable = false)
    private String content;

    @Column(name = "content_html", columnDefinition = "TEXT", nullable = false)
    private String contentHtml;

    @Column(name = "is_pinned")
    private Boolean isPinned = false;

    @Column(name = "is_locked")
    private Boolean isLocked = false;

    @Column(name = "view_count")
    private Integer viewCount = 0;

    @Column(name = "reply_count")
    private Integer replyCount = 0;

    @Column(name = "like_count")
    private Integer likeCount = 0;

    @Column(name = "last_reply_at")
    private LocalDateTime lastReplyAt;
}
