package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.entity.LoginHistory;
import com.qoobot.qooauth.auth.entity.TrustedDevice;
import com.qoobot.qooauth.auth.service.AccountSecurityService;
import com.qoobot.qooauth.common.dto.ApiResponse;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.data.domain.Page;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/auth/security")
public class AccountSecurityController {

    private final AccountSecurityService securityService;

    public AccountSecurityController(AccountSecurityService securityService) {
        this.securityService = securityService;
    }

    // ========================================================================
    // Password Change
    // ========================================================================

    /**
     * POST /api/v1/auth/security/password/change
     * Change password for authenticated user.
     * Body: { "current_password": "...", "new_password": "...", "revoke_sessions": true }
     */
    @PostMapping("/password/change")
    public ResponseEntity<ApiResponse<Map<String, Object>>> changePassword(
            @RequestAttribute("userId") String userId,
            @RequestBody Map<String, Object> body) {

        String currentPassword = (String) body.get("current_password");
        String newPassword = (String) body.get("new_password");
        boolean revokeSessions = body.get("revoke_sessions") != null
                && Boolean.TRUE.equals(body.get("revoke_sessions"));

        if (currentPassword == null || newPassword == null) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error("BAD_REQUEST",
                            "current_password and new_password are required"));
        }

        Instant changedAt = securityService.changePassword(
                userId, currentPassword, newPassword, revokeSessions);

        return ResponseEntity.ok(ApiResponse.ok(Map.of(
                "changed_at", changedAt.toString(),
                "message", "Password changed successfully"
        )));
    }

    // ========================================================================
    // Trusted Devices
    // ========================================================================

    /**
     * GET /api/v1/auth/security/devices
     * List all trusted devices for the authenticated user.
     */
    @GetMapping("/devices")
    public ResponseEntity<ApiResponse<List<TrustedDevice>>> listDevices(
            @RequestAttribute("userId") String userId) {

        List<TrustedDevice> devices = securityService.getTrustedDevices(userId);
        return ResponseEntity.ok(ApiResponse.ok(devices));
    }

    /**
     * POST /api/v1/auth/security/devices/{deviceId}/trust
     * Mark a device as trusted (for 2FA bypass on this device).
     */
    @PostMapping("/devices/{deviceId}/trust")
    public ResponseEntity<ApiResponse<Map<String, Object>>> trustDevice(
            @RequestAttribute("userId") String userId,
            @PathVariable String deviceId) {

        securityService.trustDevice(userId, deviceId);
        return ResponseEntity.ok(ApiResponse.ok(Map.of(
                "device_id", deviceId,
                "trusted", true
        )));
    }

    /**
     * DELETE /api/v1/auth/security/devices/{deviceId}
     * Remove a specific trusted device.
     */
    @DeleteMapping("/devices/{deviceId}")
    public ResponseEntity<ApiResponse<Map<String, Object>>> removeDevice(
            @RequestAttribute("userId") String userId,
            @PathVariable String deviceId) {

        securityService.removeDevice(userId, deviceId);
        return ResponseEntity.ok(ApiResponse.ok(Map.of(
                "device_id", deviceId,
                "removed", true
        )));
    }

    /**
     * DELETE /api/v1/auth/security/devices
     * Remove all trusted devices (logout all).
     */
    @DeleteMapping("/devices")
    public ResponseEntity<ApiResponse<Map<String, Object>>> removeAllDevices(
            @RequestAttribute("userId") String userId) {

        securityService.removeAllDevices(userId);
        return ResponseEntity.ok(ApiResponse.ok(Map.of(
                "message", "All trusted devices removed"
        )));
    }

    /**
     * POST /api/v1/auth/security/devices/record
     * Record a device after login (called by frontend with device info).
     * Body: { "device_name", "device_type", "os_name", "os_version",
     *         "browser_name", "browser_version", "device_model", "fingerprint" }
     */
    @PostMapping("/devices/record")
    public ResponseEntity<ApiResponse<TrustedDevice>> recordDevice(
            @RequestAttribute("userId") String userId,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request) {

        String deviceId = (String) body.getOrDefault("device_id", null);
        String deviceName = (String) body.get("device_name");
        String deviceType = (String) body.getOrDefault("device_type", "browser");
        String osName = (String) body.get("os_name");
        String osVersion = (String) body.get("os_version");
        String browserName = (String) body.get("browser_name");
        String browserVersion = (String) body.get("browser_version");
        String deviceModel = (String) body.get("device_model");
        String fingerprint = (String) body.get("fingerprint");
        String userAgent = request.getHeader("User-Agent");
        String ip = getClientIp(request);

        TrustedDevice device = securityService.recordTrustedDevice(
                userId, deviceId, deviceName, deviceType,
                osName, osVersion, browserName, browserVersion,
                deviceModel, fingerprint, ip, userAgent);

        return ResponseEntity.ok(ApiResponse.ok(device));
    }

    // ========================================================================
    // Login History
    // ========================================================================

    /**
     * GET /api/v1/auth/security/login-history?page=0&size=20
     * Get paginated login history for the authenticated user.
     */
    @GetMapping("/login-history")
    public ResponseEntity<ApiResponse<Page<LoginHistory>>> getLoginHistory(
            @RequestAttribute("userId") String userId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {

        if (size > 100) size = 100;
        Page<LoginHistory> history = securityService.getLoginHistory(userId, page, size);
        return ResponseEntity.ok(ApiResponse.ok(history));
    }

    // ========================================================================
    // Helpers
    // ========================================================================

    private String getClientIp(HttpServletRequest request) {
        String xForwardedFor = request.getHeader("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
