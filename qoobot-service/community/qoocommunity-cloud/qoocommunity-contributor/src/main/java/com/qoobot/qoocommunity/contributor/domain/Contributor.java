package com.qoobot.qoocommunity.contributor.domain;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "contributors")
public class Contributor {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false, unique = true, length = 64)
    private String userId;

    @Column(name = "cla_signed")
    private Boolean claSigned = false;

    @Column(name = "cla_signed_at")
    private LocalDateTime claSignedAt;

    @Column(name = "cla_type", length = 20)
    private String claType;

    @Column(length = 20)
    private String level = "CONTRIBUTOR";

    @Column(name = "pr_count")
    private Integer prCount = 0;

    @Column(name = "commit_count")
    private Integer commitCount = 0;

    @Column(name = "review_count")
    private Integer reviewCount = 0;

    @Column(name = "active_months")
    private Integer activeMonths = 0;

    @Column(name = "joined_at")
    private LocalDateTime joinedAt = LocalDateTime.now();

    @Column(name = "promoted_at")
    private LocalDateTime promotedAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();
}
