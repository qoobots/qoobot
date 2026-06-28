package com.qoobot.qoocommunity.governance.domain;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "governance_sigs")
public class Sig {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 200)
    private String name;

    @Column(nullable = false, unique = true, length = 100)
    private String slug;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "chair_id", length = 64)
    private String chairId;

    @Column(name = "member_count")
    private Integer memberCount = 0;

    @Column(name = "meeting_schedule", length = 200)
    private String meetingSchedule;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();
}
