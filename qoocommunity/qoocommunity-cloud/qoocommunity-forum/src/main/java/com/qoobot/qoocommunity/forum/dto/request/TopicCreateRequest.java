package com.qoobot.qoocommunity.forum.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Data
public class TopicCreateRequest {

    @NotNull
    private Long categoryId;

    @NotBlank
    private String title;

    @NotBlank
    private String content;

    @NotBlank
    private String contentHtml;

    private List<String> tags;
}
