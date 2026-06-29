package com.qoobot.qoocommunity.governance.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class VoteRequest {

    @NotBlank
    private String vote;

    private String comment;
}
