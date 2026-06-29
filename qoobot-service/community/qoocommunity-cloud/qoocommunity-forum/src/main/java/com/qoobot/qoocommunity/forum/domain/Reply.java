package com.qoobot.qoocommunity.forum.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@Entity
@Table(name = "forum_replies")
@EqualsAndHashCode(callSuper = true)
public class Reply extends com.qoobot.qoocommunity.common.entity.BaseEntity {

    @Column(name = "topic_id", nullable = false)
    private Long topicId;

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    @Column(name = "parent_id")
    private Long parentId;

    @Column(columnDefinition = "TEXT", nullable = false)
    private String content;

    @Column(name = "content_html", columnDefinition = "TEXT", nullable = false)
    private String contentHtml;

    @Column(name = "like_count")
    private Integer likeCount = 0;
}
