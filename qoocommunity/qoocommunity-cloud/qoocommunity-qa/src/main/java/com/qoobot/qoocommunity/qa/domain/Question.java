package com.qoobot.qoocommunity.qa.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@Entity
@Table(name = "qa_questions")
@EqualsAndHashCode(callSuper = true)
public class Question extends com.qoobot.qoocommunity.common.entity.BaseEntity {

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    @Column(nullable = false, length = 500)
    private String title;

    @Column(columnDefinition = "TEXT", nullable = false)
    private String content;

    @Column(name = "content_html", columnDefinition = "TEXT", nullable = false)
    private String contentHtml;

    @Column(name = "view_count")
    private Integer viewCount = 0;

    @Column(name = "answer_count")
    private Integer answerCount = 0;

    @Column(name = "vote_score")
    private Integer voteScore = 0;

    @Column(name = "accepted_answer_id")
    private Long acceptedAnswerId;

    @Column(name = "is_solved")
    private Boolean isSolved = false;
}
