package com.qoobot.qoocommunity.qa.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class AnswerCreateRequest {

    @NotBlank
    private String content;

    @NotBlank
    private String contentHtml;
}
