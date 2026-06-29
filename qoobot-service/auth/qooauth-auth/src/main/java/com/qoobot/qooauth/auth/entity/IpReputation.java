package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * IP reputation entity for tracking IP address trust scores.
 * Used for brute-force and credential stuffing detection.
 */
@Entity
@Table(name = "ip_reputation")
public class IpReputation {

    @Id
    @Column(name = "reputation_id", length = 64)
    private String reputationId;

    @Column(name = "ip_address", nullable = false, length = 45)
    private String ipAddress;

    @Column(name = "ip_version", nullable = false, length = 4)
    private String ipVersion = "v4";

    @Column(name = "total_attempts", nullable = false)
    private long totalAttempts = 0;

    @Column(name = "failure_count", nullable = false)
    private long failureCount = 0;

    @Column(name = "success_count", nullable = false)
    private long successCount = 0;

    @Column(name = "last_seen_at")
    private Instant lastSeenAt;

    @Column(name = "first_seen_at")
    private Instant firstSeenAt;

    @Column(name = "is_blocked", nullable = false)
    private boolean blocked = false;

    @Column(name = "blocked_at")
    private Instant blockedAt;

    @Column(name = "blocked_reason", length = 256)
    private String blockedReason;

    @Column(name = "risk_score", nullable = false)
    private double riskScore = 0.0;

    @Column(name = "geo_country", length = 8)
    private String geoCountry;

    @Column(name = "geo_city", length = 128)
    private String geoCity;

    @Column(name = "isp_name", length = 128)
    private String ispName;

    @Column(name = "is_datacenter", nullable = false)
    private boolean datacenter = false;

    @Column(name = "is_tor_exit", nullable = false)
    private boolean torExit = false;

    @Column(name = "is_vpn", nullable = false)
    private boolean vpn = false;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    // --- Getters and Setters ---

    public String getReputationId() { return reputationId; }
    public void setReputationId(String reputationId) { this.reputationId = reputationId; }

    public String getIpAddress() { return ipAddress; }
    public void setIpAddress(String ipAddress) { this.ipAddress = ipAddress; }

    public String getIpVersion() { return ipVersion; }
    public void setIpVersion(String ipVersion) { this.ipVersion = ipVersion; }

    public long getTotalAttempts() { return totalAttempts; }
    public void setTotalAttempts(long totalAttempts) { this.totalAttempts = totalAttempts; }

    public long getFailureCount() { return failureCount; }
    public void setFailureCount(long failureCount) { this.failureCount = failureCount; }

    public long getSuccessCount() { return successCount; }
    public void setSuccessCount(long successCount) { this.successCount = successCount; }

    public Instant getLastSeenAt() { return lastSeenAt; }
    public void setLastSeenAt(Instant lastSeenAt) { this.lastSeenAt = lastSeenAt; }

    public Instant getFirstSeenAt() { return firstSeenAt; }
    public void setFirstSeenAt(Instant firstSeenAt) { this.firstSeenAt = firstSeenAt; }

    public boolean isBlocked() { return blocked; }
    public void setBlocked(boolean blocked) { this.blocked = blocked; }

    public Instant getBlockedAt() { return blockedAt; }
    public void setBlockedAt(Instant blockedAt) { this.blockedAt = blockedAt; }

    public String getBlockedReason() { return blockedReason; }
    public void setBlockedReason(String blockedReason) { this.blockedReason = blockedReason; }

    public double getRiskScore() { return riskScore; }
    public void setRiskScore(double riskScore) { this.riskScore = riskScore; }

    public String getGeoCountry() { return geoCountry; }
    public void setGeoCountry(String geoCountry) { this.geoCountry = geoCountry; }

    public String getGeoCity() { return geoCity; }
    public void setGeoCity(String geoCity) { this.geoCity = geoCity; }

    public String getIspName() { return ispName; }
    public void setIspName(String ispName) { this.ispName = ispName; }

    public boolean isDatacenter() { return datacenter; }
    public void setDatacenter(boolean datacenter) { this.datacenter = datacenter; }

    public boolean isTorExit() { return torExit; }
    public void setTorExit(boolean torExit) { this.torExit = torExit; }

    public boolean isVpn() { return vpn; }
    public void setVpn(boolean vpn) { this.vpn = vpn; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
