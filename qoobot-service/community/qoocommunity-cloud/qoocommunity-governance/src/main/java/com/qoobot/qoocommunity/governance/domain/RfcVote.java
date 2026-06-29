package com.qoobot.qoocommunity.governance.domain;

import com.qoobot.qoocommunity.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "governance_rfc_votes")
@EqualsAndHashCode(callSuper = true)
public class RfcVote extends BaseEntity {

    @Column(name = "rfc_id", nullable = false)
    private Long rfcId;

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    @Column(nullable = false, length = 10)
    private String vote;

    @Column(columnDefinition = "TEXT")
    private String comment;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();
}
