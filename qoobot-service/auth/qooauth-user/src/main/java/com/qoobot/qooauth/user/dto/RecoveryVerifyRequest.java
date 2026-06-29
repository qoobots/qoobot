package com.qoobot.qooauth.user.dto;

import jakarta.validation.constraints.NotBlank;

public class RecoveryVerifyRequest {
    @NotBlank
    private String sessionToken;
    @NotBlank
    private String code;  // recovery code or verification code

    public String getSessionToken() { return sessionToken; }
    public void setSessionToken(String sessionToken) { this.sessionToken = sessionToken; }
    public String getCode() { return code; }
    public void setCode(String code) { this.code = code; }
}
