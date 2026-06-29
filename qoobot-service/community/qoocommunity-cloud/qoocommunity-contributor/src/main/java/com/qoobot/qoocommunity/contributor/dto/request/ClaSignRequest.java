package com.qoobot.qoocommunity.contributor.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class ClaSignRequest {

    @NotBlank
    private String claType;
}
