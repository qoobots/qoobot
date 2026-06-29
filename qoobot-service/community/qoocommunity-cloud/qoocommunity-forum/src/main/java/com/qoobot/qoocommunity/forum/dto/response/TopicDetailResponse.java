package com.qoobot.qoocommunity.forum.dto.response;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
public class TopicDetailResponse {

    private Long id;
    private Long categoryId;
    private String categoryName;
    private String userId;
    private String nickname;
    private String avatarUrl;
    private String title;
    private String content;
    private String contentHtml;
    private Boolean isPinned;
    private Boolean isLocked;
    private Integer viewCount;
    private Integer replyCount;
    private Integer likeCount;
    private Boolean isLiked;
    private Boolean isBookmarked;
    private List<String> tags;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private LocalDateTime lastReplyAt;
}
