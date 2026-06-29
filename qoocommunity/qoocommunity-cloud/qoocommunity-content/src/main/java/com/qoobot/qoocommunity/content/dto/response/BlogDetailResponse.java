package com.qoobot.qoocommunity.content.dto.response;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
public class BlogDetailResponse {

    private Long id;
    private String title;
    private String slug;
    private String summary;
    private String content;
    private String contentHtml;
    private String coverUrl;
    private String authorId;
    private String authorName;
    private String authorAvatarUrl;
    private List<String> tags;
    private Integer viewCount;
    private LocalDateTime publishedAt;
    private LocalDateTime createdAt;
}
