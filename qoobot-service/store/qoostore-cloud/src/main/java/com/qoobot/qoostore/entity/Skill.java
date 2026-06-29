package com.qoobot.qoostore.entity;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "skills")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Skill {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "skill_id", nullable = false, unique = true, length = 255)
    private String skillId;

    @Column(nullable = false, length = 128)
    private String name;

    @Column(name = "developer_id", nullable = false)
    private Long developerId;

    @Column(name = "category_id")
    private Long categoryId;

    @Column(length = 255)
    private String tagline;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "icon_url", length = 1024)
    private String iconUrl;

    @Column(name = "privacy_level", length = 16)
    @Builder.Default
    private String privacyLevel = "public";

    @Column(length = 16)
    @Builder.Default
    private String status = "draft";

    @Column(name = "pricing_model", length = 32)
    @Builder.Default
    private String pricingModel = "free";

    @Column(precision = 10, scale = 2)
    @Builder.Default
    private BigDecimal price = BigDecimal.ZERO;

    @Column(length = 3)
    @Builder.Default
    private String currency = "USD";

    @Column(name = "trial_days")
    @Builder.Default
    private Integer trialDays = 0;

    @Column(name = "created_at")
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    @Builder.Default
    private LocalDateTime updatedAt = LocalDateTime.now();

    @Column(name = "published_at")
    private LocalDateTime publishedAt;

    @PreUpdate
    public void preUpdate() {
        this.updatedAt = LocalDateTime.now();
    }
}
