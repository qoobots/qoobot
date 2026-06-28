package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.entity.DeviceFingerprint;
import com.qoobot.qooauth.auth.service.BruteForceProtectionService;
import com.qoobot.qooauth.auth.service.DeviceFingerprintService;
import com.qoobot.qooauth.common.dto.ApiResponse;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * Threat Protection Controller.
 * <p>
 * Endpoints for:
 * <ul>
 *   <li>Brute-force protection status queries</li>
 *   <li>CAPTCHA requirement checks</li>
 *   <li>Device fingerprint management</li>
 *   <li>Manual unblocking (admin)</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/v1/auth/security/threat")
public class ThreatProtectionController {

    private final BruteForceProtectionService bruteForceProtectionService;
    private final DeviceFingerprintService deviceFingerprintService;

    public ThreatProtectionController(BruteForceProtectionService bruteForceProtectionService,
                                       DeviceFingerprintService deviceFingerprintService) {
        this.bruteForceProtectionService = bruteForceProtectionService;
        this.deviceFingerprintService = deviceFingerprintService;
    }

    /**
     * Check if CAPTCHA is required for the given email before login.
     */
    @GetMapping("/captcha-required")
    public ApiResponse<Map<String, Object>> checkCaptchaRequired(@RequestParam String email) {
        boolean required = bruteForceProtectionService.isCaptchaRequired(email);
        int failureCount = bruteForceProtectionService.getAccountFailureCount(email);
        return ApiResponse.ok(Map.of(
                "email", email,
                "captcha_required", required,
                "failure_count", failureCount
        ));
    }

    /**
     * Get brute-force protection status for an account.
     */
    @GetMapping("/account-status")
    public ApiResponse<Map<String, Object>> getAccountStatus(@RequestParam String email) {
        boolean blocked = bruteForceProtectionService.isAccountBlocked(email);
        boolean captchaRequired = bruteForceProtectionService.isCaptchaRequired(email);
        int failureCount = bruteForceProtectionService.getAccountFailureCount(email);
        return ApiResponse.ok(Map.of(
                "email", email,
                "blocked", blocked,
                "captcha_required", captchaRequired,
                "failure_count", failureCount
        ));
    }

    /**
     * Get IP failure count.
     */
    @GetMapping("/ip-status")
    public ApiResponse<Map<String, Object>> getIpStatus(@RequestParam String ip) {
        int failureCount = bruteForceProtectionService.getIpFailureCount(ip);
        return ApiResponse.ok(Map.of(
                "ip", ip,
                "failure_count", failureCount
        ));
    }

    /**
     * Unblock an account (admin only).
     */
    @PostMapping("/unblock-account")
    public ApiResponse<Map<String, String>> unblockAccount(@RequestBody Map<String, String> body) {
        String email = body.get("email");
        if (email == null || email.isEmpty()) {
            return ApiResponse.error("BAD_REQUEST", "email is required");
        }
        bruteForceProtectionService.unblockAccount(email);
        return ApiResponse.ok(Map.of("email", email, "status", "unblocked"));
    }

    /**
     * Unblock an IP (admin only).
     */
    @PostMapping("/unblock-ip")
    public ApiResponse<Map<String, String>> unblockIp(@RequestBody Map<String, String> body) {
        String ip = body.get("ip");
        if (ip == null || ip.isEmpty()) {
            return ApiResponse.error("BAD_REQUEST", "ip is required");
        }
        bruteForceProtectionService.unblockIp(ip);
        return ApiResponse.ok(Map.of("ip", ip, "status", "unblocked"));
    }

    /**
     * Record a device fingerprint.
     */
    @PostMapping("/device-fingerprint")
    public ApiResponse<DeviceFingerprint> recordFingerprint(
            @RequestBody Map<String, Object> body) {
        String userId = (String) body.get("user_id");
        String deviceType = (String) body.getOrDefault("device_type", "browser");
        String browserName = (String) body.get("browser_name");
        String browserVersion = (String) body.get("browser_version");
        String osName = (String) body.get("os_name");
        String osVersion = (String) body.get("os_version");
        String screenResolution = (String) body.get("screen_resolution");
        int timezoneOffset = (Integer) body.getOrDefault("timezone_offset", 0);
        String language = (String) body.get("language");
        String canvasHash = (String) body.get("canvas_hash");
        String webglHash = (String) body.get("webgl_hash");
        String fontHash = (String) body.get("font_hash");

        DeviceFingerprint fp = deviceFingerprintService.recordFingerprint(
                userId, deviceType, browserName, browserVersion,
                osName, osVersion, screenResolution, timezoneOffset,
                language, canvasHash, webglHash, fontHash);
        return ApiResponse.ok(fp);
    }

    /**
     * Get device fingerprints for a user.
     */
    @GetMapping("/device-fingerprints/{userId}")
    public ApiResponse<List<DeviceFingerprint>> getUserFingerprints(@PathVariable String userId) {
        List<DeviceFingerprint> fps = deviceFingerprintService.getUserFingerprints(userId);
        return ApiResponse.ok(fps);
    }

    /**
     * Check if a device is known for a user.
     */
    @PostMapping("/device-fingerprint/check-known")
    public ApiResponse<Map<String, Object>> checkKnownDevice(
            @RequestBody Map<String, String> body) {
        String userId = body.get("user_id");
        String canvasHash = body.get("canvas_hash");
        String webglHash = body.get("webgl_hash");
        String fontHash = body.get("font_hash");
        String osName = body.get("os_name");
        String browserName = body.get("browser_name");

        boolean known = deviceFingerprintService.isKnownDevice(
                userId, canvasHash, webglHash, fontHash, osName, browserName);
        return ApiResponse.ok(Map.of("known", known));
    }
}
