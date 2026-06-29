package com.qoobot.qoocommunity.forum.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class ReplyCreateRequest {

    private Long parentId;

    @NotBlank
    private String content;

    @NotBlank
    private String contentHtml;
}
