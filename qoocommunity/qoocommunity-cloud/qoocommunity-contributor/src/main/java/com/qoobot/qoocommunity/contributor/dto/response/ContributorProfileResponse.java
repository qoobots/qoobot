package com.qoobot.qoocommunity.contributor.dto.response;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class ContributorProfileResponse {

    private String userId;
    private String nickname;
    private String avatarUrl;
    private String level;
    private Boolean claSigned;
    private LocalDateTime claSignedAt;
    private String claType;
    private Integer prCount;
    private Integer commitCount;
    private Integer reviewCount;
    private Integer activeMonths;
    private LocalDateTime joinedAt;
}
