package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * Device fingerprint entity for browser/device identity tracking.
 * Stores canvas/WebGL/font hashes for device recognition and fraud detection.
 */
@Entity
@Table(name = "device_fingerprints")
public class DeviceFingerprint {

    @Id
    @Column(name = "fingerprint_id", length = 64)
    private String fingerprintId;

    @Column(name = "user_id", nullable = false, length = 32)
    private String userId;

    @Column(name = "fingerprint_hash", nullable = false, length = 256)
    private String fingerprintHash;

    @Column(name = "device_type", length = 32)
    private String deviceType;

    @Column(name = "browser_name", length = 64)
    private String browserName;

    @Column(name = "browser_version", length = 32)
    private String browserVersion;

    @Column(name = "os_name", length = 64)
    private String osName;

    @Column(name = "os_version", length = 32)
    private String osVersion;

    @Column(name = "screen_resolution", length = 16)
    private String screenResolution;

    @Column(name = "timezone_offset")
    private Integer timezoneOffset;

    @Column(length = 10)
    private String language;

    @Column(name = "canvas_hash", length = 64)
    private String canvasHash;

    @Column(name = "webgl_hash", length = 64)
    private String webglHash;

    @Column(name = "font_hash", length = 64)
    private String fontHash;

    @Column(name = "first_seen_at", nullable = false)
    private Instant firstSeenAt;

    @Column(name = "last_seen_at", nullable = false)
    private Instant lastSeenAt;

    @Column(name = "use_count", nullable = false)
    private int useCount = 1;

    @Column(name = "risk_score", nullable = false)
    private double riskScore = 0.0;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    // --- Getters and Setters ---

    public String getFingerprintId() { return fingerprintId; }
    public void setFingerprintId(String fingerprintId) { this.fingerprintId = fingerprintId; }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getFingerprintHash() { return fingerprintHash; }
    public void setFingerprintHash(String fingerprintHash) { this.fingerprintHash = fingerprintHash; }

    public String getDeviceType() { return deviceType; }
    public void setDeviceType(String deviceType) { this.deviceType = deviceType; }

    public String getBrowserName() { return browserName; }
    public void setBrowserName(String browserName) { this.browserName = browserName; }

    public String getBrowserVersion() { return browserVersion; }
    public void setBrowserVersion(String browserVersion) { this.browserVersion = browserVersion; }

    public String getOsName() { return osName; }
    public void setOsName(String osName) { this.osName = osName; }

    public String getOsVersion() { return osVersion; }
    public void setOsVersion(String osVersion) { this.osVersion = osVersion; }

    public String getScreenResolution() { return screenResolution; }
    public void setScreenResolution(String screenResolution) { this.screenResolution = screenResolution; }

    public Integer getTimezoneOffset() { return timezoneOffset; }
    public void setTimezoneOffset(Integer timezoneOffset) { this.timezoneOffset = timezoneOffset; }

    public String getLanguage() { return language; }
    public void setLanguage(String language) { this.language = language; }

    public String getCanvasHash() { return canvasHash; }
    public void setCanvasHash(String canvasHash) { this.canvasHash = canvasHash; }

    public String getWebglHash() { return webglHash; }
    public void setWebglHash(String webglHash) { this.webglHash = webglHash; }

    public String getFontHash() { return fontHash; }
    public void setFontHash(String fontHash) { this.fontHash = fontHash; }

    public Instant getFirstSeenAt() { return firstSeenAt; }
    public void setFirstSeenAt(Instant firstSeenAt) { this.firstSeenAt = firstSeenAt; }

    public Instant getLastSeenAt() { return lastSeenAt; }
    public void setLastSeenAt(Instant lastSeenAt) { this.lastSeenAt = lastSeenAt; }

    public int getUseCount() { return useCount; }
    public void setUseCount(int useCount) { this.useCount = useCount; }

    public double getRiskScore() { return riskScore; }
    public void setRiskScore(double riskScore) { this.riskScore = riskScore; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
}
