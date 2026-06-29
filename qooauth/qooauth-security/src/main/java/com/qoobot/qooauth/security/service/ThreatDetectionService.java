package com.qoobot.qooauth.security.service;

import com.qoobot.qooauth.security.dto.ThreatDetectionRequest;
import com.qoobot.qooauth.security.entity.SecurityEvent;
import com.qoobot.qooauth.security.repository.SecurityEventRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

/**
 * Anomaly detection service for login threat analysis.
 * <p>
 * Scores login attempts across 6 weighted dimensions:
 * <ul>
 *   <li>Device fingerprint (25%) - known device vs new/spoofed</li>
 *   <li>IP reputation (20%) - VPN/TOR/proxy detection, known bad IPs</li>
 *   <li>Geo-location (15%) - impossible travel, unusual location</li>
 *   <li>Behavior (20%) - rapid attempts, unusual time patterns</li>
 *   <li>Time (10%) - off-hours access, unusual access time</li>
 *   <li>Network (10%) - network type, ASN reputation</li>
 * </ul>
 * A composite risk score >= 0.7 triggers automated response (CAPTCHA, rate limit, or ban).
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ThreatDetectionService {

    private static final double RISK_THRESHOLD_HIGH = 0.8;
    private static final double RISK_THRESHOLD_MEDIUM = 0.7;
    private static final double RISK_THRESHOLD_LOW = 0.5;

    // Dimension weights (must sum to 1.0)
    private static final double WEIGHT_DEVICE = 0.25;
    private static final double WEIGHT_IP = 0.20;
    private static final double WEIGHT_GEO = 0.15;
    private static final double WEIGHT_BEHAVIOR = 0.20;
    private static final double WEIGHT_TIME = 0.10;
    private static final double WEIGHT_NETWORK = 0.10;

    private final SecurityEventRepository securityEventRepository;

    /**
     * Analyze a login attempt and return a threat assessment.
     *
     * @param request the threat detection request with login context
     * @return threat assessment result including composite score and response action
     */
    public Map<String, Object> analyzeLoginThreat(ThreatDetectionRequest request) {
        log.info("Analyzing login threat for user: {}, ip: {}", request.getUserId(), request.getSourceIp());

        // Score each dimension independently
        double deviceScore = scoreDeviceDimension(request);
        double ipScore = scoreIpDimension(request);
        double geoScore = scoreGeoDimension(request);
        double behaviorScore = scoreBehaviorDimension(request);
        double timeScore = scoreTimeDimension(request);
        double networkScore = scoreNetworkDimension(request);

        // Compute weighted composite score
        double compositeScore = (deviceScore * WEIGHT_DEVICE)
                + (ipScore * WEIGHT_IP)
                + (geoScore * WEIGHT_GEO)
                + (behaviorScore * WEIGHT_BEHAVIOR)
                + (timeScore * WEIGHT_TIME)
                + (networkScore * WEIGHT_NETWORK);

        // Clamp to [0, 1]
        compositeScore = Math.max(0.0, Math.min(1.0, compositeScore));

        String severity;
        String action;
        if (compositeScore >= RISK_THRESHOLD_HIGH) {
            severity = "CRITICAL";
            action = "BLOCK";
        } else if (compositeScore >= RISK_THRESHOLD_MEDIUM) {
            severity = "HIGH";
            action = "CAPTCHA";
        } else if (compositeScore >= RISK_THRESHOLD_LOW) {
            severity = "MEDIUM";
            action = "MONITOR";
        } else {
            severity = "LOW";
            action = "ALLOW";
        }

        // Persist security event if threat detected
        if (compositeScore >= RISK_THRESHOLD_MEDIUM) {
            SecurityEvent event = SecurityEvent.builder()
                    .userId(request.getUserId())
                    .eventType("LOGIN_ANOMALY")
                    .severity(severity)
                    .sourceIp(request.getSourceIp())
                    .details(buildEventDetails(request, compositeScore, deviceScore, ipScore,
                            geoScore, behaviorScore, timeScore, networkScore))
                    .detectedAt(Instant.now())
                    .build();
            securityEventRepository.save(event);
            log.warn("Threat detected: userId={}, score={}, severity={}, action={}",
                    request.getUserId(), String.format("%.3f", compositeScore), severity, action);
        }

        Map<String, Object> result = new HashMap<>();
        result.put("userId", request.getUserId());
        result.put("compositeRiskScore", Math.round(compositeScore * 1000.0) / 1000.0);
        result.put("severity", severity);
        result.put("recommendedAction", action);
        result.put("dimensionScores", Map.of(
                "device", Math.round(deviceScore * 1000.0) / 1000.0,
                "ipReputation", Math.round(ipScore * 1000.0) / 1000.0,
                "geo", Math.round(geoScore * 1000.0) / 1000.0,
                "behavior", Math.round(behaviorScore * 1000.0) / 1000.0,
                "time", Math.round(timeScore * 1000.0) / 1000.0,
                "network", Math.round(networkScore * 1000.0) / 1000.0
        ));

        return result;
    }

    // ---- Dimension scoring methods ----

    private double scoreDeviceDimension(ThreatDetectionRequest request) {
        // Higher risk when no fingerprint or unknown fingerprint is provided
        if (request.getFingerprintHash() == null || request.getFingerprintHash().isBlank()) {
            return 0.8; // No fingerprint = suspicious
        }
        // In production, compare against known device fingerprints in DB
        // Placeholder: assume moderate risk for new fingerprints
        return 0.3;
    }

    private double scoreIpDimension(ThreatDetectionRequest request) {
        double score = 0.0;
        // Check for known bad IP patterns (placeholder logic)
        String ip = request.getSourceIp();
        if (ip == null || ip.isBlank()) {
            return 0.9;
        }
        // VPN/TOR/Proxy detection based on network type
        String networkType = request.getNetworkType();
        if (networkType != null) {
            switch (networkType.toUpperCase()) {
                case "TOR" -> score = 0.9;
                case "VPN" -> score = 0.6;
                case "PROXY" -> score = 0.7;
                case "MOBILE" -> score = 0.2;
                case "RESIDENTIAL" -> score = 0.1;
                default -> score = 0.3;
            }
        }
        return score;
    }

    private double scoreGeoDimension(ThreatDetectionRequest request) {
        double score = 0.0;
        // Check for impossible travel or unusual geo patterns
        if (request.getGeoCountry() == null) {
            return 0.5; // Unknown location = moderate risk
        }
        // High-risk jurisdictions (placeholder)
        String country = request.getGeoCountry().toUpperCase();
        if ("KP".equals(country) || "IR".equals(country)) {
            score = 0.8;
        }
        return score;
    }

    private double scoreBehaviorDimension(ThreatDetectionRequest request) {
        double score = 0.0;
        // Failed login attempts indicate potential brute force / credential stuffing
        Integer failedAttempts = request.getRecentFailedAttempts();
        if (failedAttempts != null) {
            if (failedAttempts >= 10) {
                score = 0.9;
            } else if (failedAttempts >= 5) {
                score = 0.6;
            } else if (failedAttempts >= 3) {
                score = 0.3;
            }
        }
        return score;
    }

    private double scoreTimeDimension(ThreatDetectionRequest request) {
        // Off-hours access is slightly more suspicious
        // Placeholder: assume normal business hours
        return 0.1;
    }

    private double scoreNetworkDimension(ThreatDetectionRequest request) {
        double score = 0.0;
        String networkType = request.getNetworkType();
        if (networkType != null) {
            switch (networkType.toUpperCase()) {
                case "TOR" -> score = 0.9;
                case "VPN" -> score = 0.5;
                case "PROXY" -> score = 0.5;
                case "MOBILE" -> score = 0.1;
                case "RESIDENTIAL" -> score = 0.05;
                default -> score = 0.2;
            }
        }
        return score;
    }

    private String buildEventDetails(ThreatDetectionRequest request, double compositeScore,
                                      double deviceScore, double ipScore, double geoScore,
                                      double behaviorScore, double timeScore, double networkScore) {
        // Simplified JSON construction to avoid ObjectMapper dependency in this service
        return String.format(
                "{\"compositeScore\":%.3f,\"deviceScore\":%.3f,\"ipScore\":%.3f,\"geoScore\":%.3f,"
                        + "\"behaviorScore\":%.3f,\"timeScore\":%.3f,\"networkScore\":%.3f,"
                        + "\"fingerprintHash\":\"%s\",\"geoCountry\":\"%s\",\"networkType\":\"%s\"}",
                compositeScore, deviceScore, ipScore, geoScore, behaviorScore, timeScore, networkScore,
                request.getFingerprintHash() != null ? request.getFingerprintHash() : "",
                request.getGeoCountry() != null ? request.getGeoCountry() : "",
                request.getNetworkType() != null ? request.getNetworkType() : ""
        );
    }
}
