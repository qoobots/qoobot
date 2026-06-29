package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.entity.AnomalyEvent;
import com.qoobot.qooauth.auth.service.AnomalyDetectionService;
import com.qoobot.qooauth.common.dto.ApiResponse;
import org.springframework.web.bind.annotation.*;

import java.time.Duration;
import java.util.List;
import java.util.Map;

/**
 * Anomaly Detection Controller.
 * <p>
 * Provides endpoints for security admins to:
 * <ul>
 *   <li>View recent anomalies for a user</li>
 *   <li>View unresolved high/critical risk anomalies</li>
 *   <li>Resolve an anomaly event</li>
 *   <li>Check IP reputation status</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/v1/auth/security/anomalies")
public class AnomalyDetectionController {

    private final AnomalyDetectionService anomalyDetectionService;

    public AnomalyDetectionController(AnomalyDetectionService anomalyDetectionService) {
        this.anomalyDetectionService = anomalyDetectionService;
    }

    /**
     * Get recent anomalies for a specific user.
     */
    @GetMapping("/user/{userId}")
    public ApiResponse<List<AnomalyEvent>> getUserAnomalies(
            @PathVariable String userId,
            @RequestParam(defaultValue = "7") int days) {
        List<AnomalyEvent> events = anomalyDetectionService
                .getRecentAnomalies(userId, Duration.ofDays(days));
        return ApiResponse.ok(events);
    }

    /**
     * Get all unresolved high/critical risk anomalies.
     */
    @GetMapping("/unresolved")
    public ApiResponse<List<AnomalyEvent>> getUnresolvedHighRisk() {
        List<AnomalyEvent> events = anomalyDetectionService.getUnresolvedHighRiskAnomalies();
        return ApiResponse.ok(events);
    }

    /**
     * Resolve an anomaly event.
     */
    @PostMapping("/{eventId}/resolve")
    public ApiResponse<Map<String, String>> resolveAnomaly(
            @PathVariable String eventId,
            @RequestBody Map<String, String> body) {
        String resolvedBy = body.getOrDefault("resolved_by", "admin");
        anomalyDetectionService.resolveAnomaly(eventId, resolvedBy);
        return ApiResponse.ok(Map.of("event_id", eventId, "status", "resolved"));
    }

    /**
     * Check if an IP address is currently blocked.
     */
    @GetMapping("/ip/{ip}/status")
    public ApiResponse<Map<String, Object>> checkIpStatus(@PathVariable String ip) {
        boolean blocked = anomalyDetectionService.isIpBlocked(ip);
        return ApiResponse.ok(Map.of(
                "ip", ip,
                "blocked", blocked
        ));
    }
}
