package com.qoobot.qoocommunity.contributor.dto.response;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class ContributorStatsResponse {

    private String userId;
    private String nickname;
    private String level;
    private Integer totalPrs;
    private Integer mergedPrs;
    private Integer issuesCreated;
    private Integer forumPosts;
    private Integer reviews;
    private Integer reputation;
}
