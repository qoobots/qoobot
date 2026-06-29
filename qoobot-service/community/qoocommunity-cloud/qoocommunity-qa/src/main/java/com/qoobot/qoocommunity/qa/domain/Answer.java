package com.qoobot.qoocommunity.qa.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@Entity
@Table(name = "qa_answers")
@EqualsAndHashCode(callSuper = true)
public class Answer extends com.qoobot.qoocommunity.common.entity.BaseEntity {

    @Column(name = "question_id", nullable = false)
    private Long questionId;

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    @Column(columnDefinition = "TEXT", nullable = false)
    private String content;

    @Column(name = "content_html", columnDefinition = "TEXT", nullable = false)
    private String contentHtml;

    @Column(name = "vote_score")
    private Integer voteScore = 0;

    @Column(name = "is_accepted")
    private Boolean isAccepted = false;
}
