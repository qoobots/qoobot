package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * Anomaly detection event for login behavior analysis.
 * Stores detected anomalies with risk scores for ML model training and real-time protection.
 */
@Entity
@Table(name = "anomaly_events")
public class AnomalyEvent {

    @Id
    @Column(name = "event_id", length = 64)
    private String eventId;

    @Column(name = "user_id", length = 32)
    private String userId;

    @Column(name = "event_type", nullable = false, length = 32)
    private String eventType;

    @Column(name = "risk_score", nullable = false)
    private double riskScore;

    @Column(name = "risk_level", nullable = false, length = 16)
    private String riskLevel;

    @Column(name = "ip_address", length = 45)
    private String ipAddress;

    @Column(name = "geo_country", length = 8)
    private String geoCountry;

    @Column(name = "geo_city", length = 128)
    private String geoCity;

    @Column(name = "device_fingerprint", length = 256)
    private String deviceFingerprint;

    @Column(name = "user_agent", length = 512)
    private String userAgent;

    @Column(name = "anomaly_reasons", columnDefinition = "jsonb")
    private String anomalyReasons;

    @Column(name = "features", columnDefinition = "jsonb")
    private String features;

    @Column(name = "action_taken", length = 32)
    private String actionTaken;

    @Column(name = "is_resolved")
    private boolean resolved = false;

    @Column(name = "resolved_by", length = 32)
    private String resolvedBy;

    @Column(name = "resolved_at")
    private Instant resolvedAt;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    // --- Getters and Setters ---

    public String getEventId() { return eventId; }
    public void setEventId(String eventId) { this.eventId = eventId; }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getEventType() { return eventType; }
    public void setEventType(String eventType) { this.eventType = eventType; }

    public double getRiskScore() { return riskScore; }
    public void setRiskScore(double riskScore) { this.riskScore = riskScore; }

    public String getRiskLevel() { return riskLevel; }
    public void setRiskLevel(String riskLevel) { this.riskLevel = riskLevel; }

    public String getIpAddress() { return ipAddress; }
    public void setIpAddress(String ipAddress) { this.ipAddress = ipAddress; }

    public String getGeoCountry() { return geoCountry; }
    public void setGeoCountry(String geoCountry) { this.geoCountry = geoCountry; }

    public String getGeoCity() { return geoCity; }
    public void setGeoCity(String geoCity) { this.geoCity = geoCity; }

    public String getDeviceFingerprint() { return deviceFingerprint; }
    public void setDeviceFingerprint(String deviceFingerprint) { this.deviceFingerprint = deviceFingerprint; }

    public String getUserAgent() { return userAgent; }
    public void setUserAgent(String userAgent) { this.userAgent = userAgent; }

    public String getAnomalyReasons() { return anomalyReasons; }
    public void setAnomalyReasons(String anomalyReasons) { this.anomalyReasons = anomalyReasons; }

    public String getFeatures() { return features; }
    public void setFeatures(String features) { this.features = features; }

    public String getActionTaken() { return actionTaken; }
    public void setActionTaken(String actionTaken) { this.actionTaken = actionTaken; }

    public boolean isResolved() { return resolved; }
    public void setResolved(boolean resolved) { this.resolved = resolved; }

    public String getResolvedBy() { return resolvedBy; }
    public void setResolvedBy(String resolvedBy) { this.resolvedBy = resolvedBy; }

    public Instant getResolvedAt() { return resolvedAt; }
    public void setResolvedAt(Instant resolvedAt) { this.resolvedAt = resolvedAt; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
}
