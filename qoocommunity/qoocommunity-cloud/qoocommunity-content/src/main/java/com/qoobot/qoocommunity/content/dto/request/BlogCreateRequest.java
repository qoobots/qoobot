package com.qoobot.qoocommunity.content.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.util.List;

@Data
public class BlogCreateRequest {

    @NotBlank
    private String title;

    @NotBlank
    private String slug;

    private String summary;

    @NotBlank
    private String content;

    @NotBlank
    private String contentHtml;

    private String coverUrl;

    private List<String> tags;
}
