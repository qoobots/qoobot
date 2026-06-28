package com.qoobot.qoocommunity.forum.domain;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "forum_bookmarks", uniqueConstraints = {
    @UniqueConstraint(columnNames = {"user_id", "topic_id"})
})
public class Bookmark {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    @Column(name = "topic_id", nullable = false)
    private Long topicId;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();
}
