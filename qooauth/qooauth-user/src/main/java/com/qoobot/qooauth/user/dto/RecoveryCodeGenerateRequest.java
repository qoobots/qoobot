package com.qoobot.qooauth.user.dto;

import jakarta.validation.constraints.NotBlank;

public class RecoveryCodeGenerateRequest {
    @NotBlank
    private String label;

    public String getLabel() { return label; }
    public void setLabel(String label) { this.label = label; }
}
