package com.qoobot.qoocommunity.governance.domain;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "governance_rfcs")
public class Rfc {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 500)
    private String title;

    @Column(nullable = false, unique = true, length = 20)
    private String number;

    @Column(length = 20)
    private String status = "DRAFT";

    @Column(columnDefinition = "TEXT", nullable = false)
    private String content;

    @Column(name = "content_html", columnDefinition = "TEXT", nullable = false)
    private String contentHtml;

    @Column(name = "author_id", nullable = false, length = 64)
    private String authorId;

    @Column(name = "sig_id")
    private Long sigId;

    @Column(name = "vote_yes")
    private Integer voteYes = 0;

    @Column(name = "vote_no")
    private Integer voteNo = 0;

    @Column(name = "vote_abstain")
    private Integer voteAbstain = 0;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();
}
