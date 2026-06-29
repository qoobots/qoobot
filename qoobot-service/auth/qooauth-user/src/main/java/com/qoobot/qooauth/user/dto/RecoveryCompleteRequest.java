package com.qoobot.qooauth.user.dto;

import jakarta.validation.constraints.NotBlank;

public class RecoveryCompleteRequest {
    @NotBlank
    private String sessionToken;
    @NotBlank
    private String newPassword;  // new password to set

    public String getSessionToken() { return sessionToken; }
    public void setSessionToken(String sessionToken) { this.sessionToken = sessionToken; }
    public String getNewPassword() { return newPassword; }
    public void setNewPassword(String newPassword) { this.newPassword = newPassword; }
}
