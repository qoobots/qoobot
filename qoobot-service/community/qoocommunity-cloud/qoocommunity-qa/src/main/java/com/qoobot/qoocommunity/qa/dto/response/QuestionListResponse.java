package com.qoobot.qoocommunity.qa.dto.response;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class QuestionListResponse {

    private Long id;
    private String userId;
    private String nickname;
    private String avatarUrl;
    private String title;
    private Integer viewCount;
    private Integer answerCount;
    private Integer voteScore;
    private Boolean isSolved;
    private List<String> tags;
    private LocalDateTime createdAt;
}
