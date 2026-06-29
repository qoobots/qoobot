package com.qoobot.qoocommunity.content.dto.response;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class ShowcaseListResponse {

    private Long id;
    private String title;
    private String description;
    private String coverUrl;
    private String authorId;
    private String authorName;
    private String authorAvatarUrl;
    private String category;
    private List<String> tags;
    private Integer likeCount;
    private Integer viewCount;
    private Boolean isFeatured;
    private String status;
    private LocalDateTime createdAt;
}
