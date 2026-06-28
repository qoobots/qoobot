package com.qoobot.qoostore.dto.response;

import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SkillResponse {
    private Long id;
    private String skillId;
    private String name;
    private Long developerId;
    private String developerName;
    private Long categoryId;
    private String categoryName;
    private String tagline;
    private String description;
    private String iconUrl;
    private String pricingModel;
    private BigDecimal price;
    private String currency;
    private Integer trialDays;
    private String status;
    private Double avgRating;
    private Long reviewCount;
    private Long downloadCount;
    private LocalDateTime publishedAt;
    private LocalDateTime updatedAt;
}
