package com.qoobot.qoocommunity.forum.dto.response;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class TopicListResponse {

    private Long id;
    private Long categoryId;
    private String categoryName;
    private String userId;
    private String nickname;
    private String avatarUrl;
    private String title;
    private Integer viewCount;
    private Integer replyCount;
    private Integer likeCount;
    private Boolean isPinned;
    private LocalDateTime createdAt;
    private LocalDateTime lastReplyAt;
}
