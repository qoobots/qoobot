package com.qoobot.qoocommunity.content.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.util.List;

@Data
public class ShowcaseSubmitRequest {

    @NotBlank
    private String title;

    private String description;
    private String contentHtml;
    private String coverUrl;
    private String videoUrl;
    private String projectUrl;
    private String category;
    private List<String> tags;
}
