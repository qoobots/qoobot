package com.qoobot.qoostore.entity;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDate;

@Entity
@Table(name = "skill_stats")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class SkillStats {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "skill_id", nullable = false)
    private Long skillId;

    @Column(nullable = false)
    private LocalDate date;

    @Builder.Default
    private Integer downloads = 0;

    @Column(name = "active_users")
    @Builder.Default
    private Integer activeUsers = 0;

    @Column(precision = 12, scale = 2)
    @Builder.Default
    private BigDecimal revenue = BigDecimal.ZERO;

    @Column(name = "crash_count")
    @Builder.Default
    private Integer crashCount = 0;

    @Column(name = "avg_rating", precision = 3, scale = 2)
    private BigDecimal avgRating;

    @Column(name = "review_count")
    @Builder.Default
    private Integer reviewCount = 0;
}
