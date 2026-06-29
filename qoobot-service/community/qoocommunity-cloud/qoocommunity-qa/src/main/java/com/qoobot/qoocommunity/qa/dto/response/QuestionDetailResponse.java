package com.qoobot.qoocommunity.qa.dto.response;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
public class QuestionDetailResponse {

    private Long id;
    private String userId;
    private String nickname;
    private String avatarUrl;
    private String title;
    private String content;
    private String contentHtml;
    private Integer viewCount;
    private Integer answerCount;
    private Integer voteScore;
    private Boolean isSolved;
    private Long acceptedAnswerId;
    private List<String> tags;
    private Integer userVote;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
