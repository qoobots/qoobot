package com.qoobot.qoocommunity.forum.dto.response;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class CategoryTreeResponse {

    private Long id;
    private String name;
    private String slug;
    private String description;
    private Integer topicCount;
    private List<CategoryTreeResponse> children;
}
