package com.qoobot.qoocommunity.governance.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class RfcCreateRequest {

    @NotBlank
    private String title;

    @NotBlank
    private String content;

    @NotBlank
    private String contentHtml;

    private Long sigId;
}
