package com.qoobot.qoocommunity.governance.domain;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDate;

@Data
@Entity
@Table(name = "governance_tsc_members")
public class TscMember {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false, unique = true, length = 64)
    private String userId;

    @Column(length = 50)
    private String role;

    @Column(name = "term_start", nullable = false)
    private LocalDate termStart;

    @Column(name = "term_end", nullable = false)
    private LocalDate termEnd;

    @Column(name = "is_active")
    private Boolean isActive = true;
}
