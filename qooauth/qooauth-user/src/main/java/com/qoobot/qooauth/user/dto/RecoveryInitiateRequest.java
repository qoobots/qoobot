package com.qoobot.qooauth.user.dto;

import jakarta.validation.constraints.NotBlank;

public class RecoveryInitiateRequest {
    @NotBlank
    private String email;       // primary email to recover

    private String method;      // RECOVERY_CODE / BACKUP_EMAIL / TRUSTED_DEVICE (auto-detect if null)

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getMethod() { return method; }
    public void setMethod(String method) { this.method = method; }
}
