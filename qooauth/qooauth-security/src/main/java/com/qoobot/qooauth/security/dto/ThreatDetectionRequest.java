package com.qoobot.qooauth.security.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * DTO for submitting a threat detection request.
 * Contains login/request context for anomaly scoring.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ThreatDetectionRequest {

    /**
     * User ID for the login attempt.
     */
    @NotBlank
    private String userId;

    /**
     * Source IP address.
     */
    @NotBlank
    private String sourceIp;

    /**
     * Device fingerprint hash.
     */
    private String fingerprintHash;

    /**
     * User-Agent string from the client.
     */
    private String userAgent;

    /**
     * Geographic country code (ISO 3166-1 alpha-2).
     */
    private String geoCountry;

    /**
     * Geographic city.
     */
    private String geoCity;

    /**
     * Geographic region/state.
     */
    private String geoRegion;

    /**
     * Login timestamp.
     */
    private String loginTimestamp;

    /**
     * Whether the login attempt was successful.
     */
    private Boolean loginSuccess;

    /**
     * Number of recent failed attempts for this account.
     */
    private Integer recentFailedAttempts;

    /**
     * Network type (e.g., "VPN", "TOR", "PROXY", "RESIDENTIAL", "MOBILE").
     */
    private String networkType;

    /**
     * Additional context for anomaly detection.
     */
    private Map<String, Object> context;
}
