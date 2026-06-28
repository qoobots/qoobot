package com.qoobot.qooauth.user.dto;

import java.time.Instant;
import java.util.List;

public class RecoverySessionResponse {
    private String sessionToken;
    private String state;
    private String method;
    private String maskedEmail;  // e.g. "u***r@example.com"
    private List<String> availableMethods;
    private Instant expiresAt;
    private int attemptsRemaining;

    public String getSessionToken() { return sessionToken; }
    public void setSessionToken(String sessionToken) { this.sessionToken = sessionToken; }
    public String getState() { return state; }
    public void setState(String state) { this.state = state; }
    public String getMethod() { return method; }
    public void setMethod(String method) { this.method = method; }
    public String getMaskedEmail() { return maskedEmail; }
    public void setMaskedEmail(String maskedEmail) { this.maskedEmail = maskedEmail; }
    public List<String> getAvailableMethods() { return availableMethods; }
    public void setAvailableMethods(List<String> availableMethods) { this.availableMethods = availableMethods; }
    public Instant getExpiresAt() { return expiresAt; }
    public void setExpiresAt(Instant expiresAt) { this.expiresAt = expiresAt; }
    public int getAttemptsRemaining() { return attemptsRemaining; }
    public void setAttemptsRemaining(int attemptsRemaining) { this.attemptsRemaining = attemptsRemaining; }
}
