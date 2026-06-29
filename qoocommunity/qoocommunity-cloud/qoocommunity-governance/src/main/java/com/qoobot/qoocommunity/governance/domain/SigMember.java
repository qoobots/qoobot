package com.qoobot.qoocommunity.governance.domain;

import com.qoobot.qoocommunity.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "governance_sig_members")
@EqualsAndHashCode(callSuper = true)
public class SigMember extends BaseEntity {

    @Column(name = "sig_id", nullable = false)
    private Long sigId;

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    @Column(length = 50)
    private String role;

    @Column(name = "joined_at")
    private LocalDateTime joinedAt = LocalDateTime.now();
}
