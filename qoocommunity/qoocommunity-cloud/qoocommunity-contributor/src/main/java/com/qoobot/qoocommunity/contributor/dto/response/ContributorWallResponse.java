package com.qoobot.qoocommunity.contributor.dto.response;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
public class ContributorWallResponse {

    private String userId;
    private String nickname;
    private String avatarUrl;
    private String level;
    private Integer prCount;
    private Integer reputation;
    private LocalDateTime joinedAt;
}
