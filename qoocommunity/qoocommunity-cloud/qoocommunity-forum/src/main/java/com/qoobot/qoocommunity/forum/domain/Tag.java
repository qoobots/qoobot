package com.qoobot.qoocommunity.forum.domain;

import jakarta.persistence.*;
import lombok.Data;

@Data
@Entity
@Table(name = "forum_tags")
public class Tag {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 50)
    private String name;

    @Column(nullable = false, unique = true, length = 50)
    private String slug;

    @Column(length = 7)
    private String color;

    @Column(name = "topic_count")
    private Integer topicCount = 0;
}
