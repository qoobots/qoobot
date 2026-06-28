package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "login_history")
public class LoginHistory {

    @Id
    @Column(name = "login_id", length = 64)
    private String loginId;

    @Column(name = "user_id", nullable = false, length = 32)
    private String userId;

    @Column(nullable = false)
    private boolean success;

    @Column(name = "failure_reason", length = 128)
    private String failureReason;

    @Column(name = "ip_address", length = 45)
    private String ipAddress;

    @Column(name = "user_agent", length = 512)
    private String userAgent;

    @Column(name = "device_fingerprint", length = 256)
    private String deviceFingerprint;

    @Column(name = "device_name", length = 128)
    private String deviceName;

    @Column(name = "geo_country", length = 8)
    private String geoCountry;

    @Column(name = "geo_city", length = 128)
    private String geoCity;

    @Column(name = "client_id", length = 64)
    private String clientId;

    @Column(name = "mfa_used")
    private boolean mfaUsed = false;

    @Column(name = "mfa_method", length = 16)
    private String mfaMethod;

    @Column(name = "session_id", length = 64)
    private String sessionId;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    // --- Getters and setters ---
    public String getLoginId() { return loginId; }
    public void setLoginId(String loginId) { this.loginId = loginId; }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public boolean isSuccess() { return success; }
    public void setSuccess(boolean success) { this.success = success; }

    public String getFailureReason() { return failureReason; }
    public void setFailureReason(String failureReason) { this.failureReason = failureReason; }

    public String getIpAddress() { return ipAddress; }
    public void setIpAddress(String ipAddress) { this.ipAddress = ipAddress; }

    public String getUserAgent() { return userAgent; }
    public void setUserAgent(String userAgent) { this.userAgent = userAgent; }

    public String getDeviceFingerprint() { return deviceFingerprint; }
    public void setDeviceFingerprint(String deviceFingerprint) { this.deviceFingerprint = deviceFingerprint; }

    public String getDeviceName() { return deviceName; }
    public void setDeviceName(String deviceName) { this.deviceName = deviceName; }

    public String getGeoCountry() { return geoCountry; }
    public void setGeoCountry(String geoCountry) { this.geoCountry = geoCountry; }

    public String getGeoCity() { return geoCity; }
    public void setGeoCity(String geoCity) { this.geoCity = geoCity; }

    public String getClientId() { return clientId; }
    public void setClientId(String clientId) { this.clientId = clientId; }

    public boolean isMfaUsed() { return mfaUsed; }
    public void setMfaUsed(boolean mfaUsed) { this.mfaUsed = mfaUsed; }

    public String getMfaMethod() { return mfaMethod; }
    public void setMfaMethod(String mfaMethod) { this.mfaMethod = mfaMethod; }

    public String getSessionId() { return sessionId; }
    public void setSessionId(String sessionId) { this.sessionId = sessionId; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
}
