package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.service.ActivationLockService;
import com.qoobot.qooauth.auth.service.GuestModeService;
import com.qoobot.qooauth.auth.service.GuestModeService.GuestSession;
import com.qoobot.qooauth.auth.service.SecureBootService;
import com.qoobot.qooauth.auth.service.SecureBootService.BootStage;
import com.qoobot.qooauth.common.dto.ApiResponse;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * Device Security Controller.
 * <p>
 * Endpoints for:
 * <ul>
 *   <li>Secure boot chain verification and signing</li>
 *   <li>Activation lock management (anti-theft)</li>
 *   <li>Guest mode sessions</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/v1/auth/devices")
public class DeviceSecurityController {

    private final SecureBootService secureBootService;
    private final ActivationLockService activationLockService;
    private final GuestModeService guestModeService;

    public DeviceSecurityController(SecureBootService secureBootService,
                                     ActivationLockService activationLockService,
                                     GuestModeService guestModeService) {
        this.secureBootService = secureBootService;
        this.activationLockService = activationLockService;
        this.guestModeService = guestModeService;
    }

    // ========================================================================
    // Secure Boot
    // ========================================================================

    /**
     * Sign a boot stage image.
     */
    @PostMapping("/{deviceId}/secure-boot/sign")
    public ApiResponse<Map<String, Object>> signBootImage(
            @PathVariable String deviceId,
            @RequestBody Map<String, Object> body) {
        try {
            String stageName = (String) body.get("stage");
            String imageHashB64 = (String) body.get("image_hash");
            int version = (Integer) body.getOrDefault("version", 1);

            BootStage stage = BootStage.valueOf(stageName.toUpperCase());
            byte[] imageHash = Base64.getDecoder().decode(imageHashB64);
            byte[] signature = secureBootService.signBootImage(deviceId, stage, imageHash, version);

            Map<String, Object> result = new HashMap<>();
            result.put("device_id", deviceId);
            result.put("stage", stage.name);
            result.put("version", version);
            result.put("signature", Base64.getEncoder().encodeToString(signature));
            return ApiResponse.ok(result);
        } catch (Exception e) {
            return ApiResponse.error("SECURE_BOOT_SIGN_FAILED", e.getMessage());
        }
    }

    /**
     * Verify a boot stage image signature.
     */
    @PostMapping("/{deviceId}/secure-boot/verify")
    public ApiResponse<Map<String, Object>> verifyBootImage(
            @PathVariable String deviceId,
            @RequestBody Map<String, Object> body) {
        try {
            String stageName = (String) body.get("stage");
            String imageHashB64 = (String) body.get("image_hash");
            int version = (Integer) body.getOrDefault("version", 1);
            String signatureB64 = (String) body.get("signature");

            BootStage stage = BootStage.valueOf(stageName.toUpperCase());
            byte[] imageHash = Base64.getDecoder().decode(imageHashB64);
            byte[] signature = Base64.getDecoder().decode(signatureB64);

            boolean valid = secureBootService.verifyBootImage(deviceId, stage, imageHash, version, signature);

            Map<String, Object> result = new HashMap<>();
            result.put("device_id", deviceId);
            result.put("stage", stage.name);
            result.put("valid", valid);
            return ApiResponse.ok(result);
        } catch (Exception e) {
            return ApiResponse.error("SECURE_BOOT_VERIFY_FAILED", e.getMessage());
        }
    }

    /**
     * Get device boot state.
     */
    @GetMapping("/{deviceId}/secure-boot/state")
    public ApiResponse<Map<String, String>> getBootState(@PathVariable String deviceId) {
        Map<String, String> state = secureBootService.getBootState(deviceId);
        return ApiResponse.ok(state);
    }

    /**
     * Check if device secure boot chain is verified.
     */
    @GetMapping("/{deviceId}/secure-boot/verified")
    public ApiResponse<Map<String, Object>> isSecureBootVerified(@PathVariable String deviceId) {
        boolean verified = secureBootService.isSecureBootVerified(deviceId);
        return ApiResponse.ok(Map.of("device_id", deviceId, "secure_boot_verified", verified));
    }

    // ========================================================================
    // Activation Lock
    // ========================================================================

    /**
     * Enable activation lock on a device.
     */
    @PostMapping("/{deviceId}/activation-lock/enable")
    public ApiResponse<Map<String, String>> enableActivationLock(
            @PathVariable String deviceId,
            @RequestBody Map<String, String> body) {
        String ownerId = body.get("owner_id");
        String ownerEmail = body.get("owner_email");

        activationLockService.enableLock(deviceId, ownerId, ownerEmail);
        return ApiResponse.ok(Map.of("device_id", deviceId, "status", "locked"));
    }

    /**
     * Disable activation lock.
     */
    @PostMapping("/{deviceId}/activation-lock/disable")
    public ApiResponse<Map<String, String>> disableActivationLock(
            @PathVariable String deviceId,
            @RequestBody Map<String, String> body) {
        String ownerId = body.get("owner_id");
        String authToken = body.get("auth_token");

        activationLockService.disableLock(deviceId, ownerId, authToken);
        return ApiResponse.ok(Map.of("device_id", deviceId, "status", "unlocked"));
    }

    /**
     * Check activation lock status.
     */
    @GetMapping("/{deviceId}/activation-lock/status")
    public ApiResponse<Map<String, Object>> getActivationLockStatus(@PathVariable String deviceId) {
        ActivationLockService.LockState state = activationLockService.getLockState(deviceId);
        Map<String, Object> result = new HashMap<>();
        result.put("device_id", deviceId);
        result.put("locked", state != null && state.locked);
        if (state != null) {
            result.put("owner_id", state.ownerId);
            result.put("enabled_at", state.enabledAt != null ? state.enabledAt.toString() : null);
            result.put("wipe_requested", state.wipeRequested);
        }
        return ApiResponse.ok(result);
    }

    /**
     * Enable lost mode.
     */
    @PostMapping("/{deviceId}/activation-lock/lost-mode")
    public ApiResponse<Map<String, String>> enableLostMode(
            @PathVariable String deviceId,
            @RequestBody Map<String, String> body) {
        String message = body.get("message");
        String contactPhone = body.get("contact_phone");

        activationLockService.enableLostMode(deviceId, message, contactPhone);
        return ApiResponse.ok(Map.of("device_id", deviceId, "lost_mode", "enabled"));
    }

    /**
     * Disable lost mode.
     */
    @DeleteMapping("/{deviceId}/activation-lock/lost-mode")
    public ApiResponse<Map<String, String>> disableLostMode(@PathVariable String deviceId) {
        activationLockService.disableLostMode(deviceId);
        return ApiResponse.ok(Map.of("device_id", deviceId, "lost_mode", "disabled"));
    }

    /**
     * Generate remote wipe token.
     */
    @PostMapping("/{deviceId}/activation-lock/wipe-token")
    public ApiResponse<Map<String, String>> generateWipeToken(@PathVariable String deviceId) {
        String token = activationLockService.generateWipeToken(deviceId);
        return ApiResponse.ok(Map.of("device_id", deviceId, "wipe_token", token));
    }

    /**
     * Execute remote wipe.
     */
    @PostMapping("/{deviceId}/activation-lock/wipe")
    public ApiResponse<Map<String, String>> remoteWipe(
            @PathVariable String deviceId,
            @RequestBody Map<String, String> body) {
        String token = body.get("wipe_token");
        boolean valid = activationLockService.verifyWipeToken(deviceId, token);
        if (!valid) {
            return ApiResponse.error("INVALID_TOKEN", "Invalid or expired wipe token");
        }
        activationLockService.triggerRemoteWipe(deviceId);
        return ApiResponse.ok(Map.of("device_id", deviceId, "status", "wipe_triggered"));
    }

    // ========================================================================
    // Guest Mode
    // ========================================================================

    /**
     * Create a guest session.
     */
    @PostMapping("/{deviceId}/guest-session")
    public ApiResponse<GuestSession> createGuestSession(
            @PathVariable String deviceId,
            @RequestBody Map<String, Object> body,
            @RequestHeader(value = "X-Forwarded-For", required = false) String forwardedFor,
            @RequestHeader(value = "User-Agent", required = false) String userAgent,
            jakarta.servlet.http.HttpServletRequest request) {
        String guestName = (String) body.getOrDefault("guest_name", "Guest");
        int durationHours = (Integer) body.getOrDefault("duration_hours", 2);

        @SuppressWarnings("unchecked")
        List<String> featuresList = (List<String>) body.get("allowed_features");
        Set<String> allowedFeatures = featuresList != null ? new HashSet<>(featuresList) : null;

        String ip = forwardedFor != null ? forwardedFor.split(",")[0].trim() : request.getRemoteAddr();

        GuestSession session = guestModeService.createGuestSession(
                deviceId, guestName, durationHours, allowedFeatures, ip, userAgent);
        return ApiResponse.ok(session);
    }

    /**
     * End a guest session.
     */
    @DeleteMapping("/{deviceId}/guest-session/{sessionId}")
    public ApiResponse<Map<String, String>> endGuestSession(
            @PathVariable String deviceId, @PathVariable String sessionId) {
        guestModeService.endGuestSession(sessionId);
        return ApiResponse.ok(Map.of("session_id", sessionId, "status", "ended"));
    }

    /**
     * Get guest session info.
     */
    @GetMapping("/{deviceId}/guest-session/{sessionId}")
    public ApiResponse<GuestSession> getGuestSession(
            @PathVariable String deviceId, @PathVariable String sessionId) {
        GuestSession session = guestModeService.getGuestSession(sessionId);
        if (session == null) {
            return ApiResponse.error("NOT_FOUND", "Guest session not found");
        }
        return ApiResponse.ok(session);
    }

    /**
     * Extend guest session.
     */
    @PostMapping("/{deviceId}/guest-session/{sessionId}/extend")
    public ApiResponse<GuestSession> extendGuestSession(
            @PathVariable String deviceId, @PathVariable String sessionId,
            @RequestBody Map<String, Integer> body) {
        int additionalHours = body.getOrDefault("additional_hours", 1);
        GuestSession session = guestModeService.extendSession(sessionId, additionalHours);
        return ApiResponse.ok(session);
    }

    /**
     * List all guest sessions on a device.
     */
    @GetMapping("/{deviceId}/guest-sessions")
    public ApiResponse<List<GuestSession>> listGuestSessions(@PathVariable String deviceId) {
        List<GuestSession> sessions = guestModeService.listDeviceGuestSessions(deviceId);
        return ApiResponse.ok(sessions);
    }

    /**
     * End all guest sessions on a device.
     */
    @DeleteMapping("/{deviceId}/guest-sessions")
    public ApiResponse<Map<String, String>> endAllGuestSessions(@PathVariable String deviceId) {
        guestModeService.endAllDeviceGuestSessions(deviceId);
        return ApiResponse.ok(Map.of("device_id", deviceId, "status", "all_sessions_ended"));
    }

    /**
     * Check if a feature is allowed for a guest session.
     */
    @GetMapping("/{deviceId}/guest-session/{sessionId}/feature-check")
    public ApiResponse<Map<String, Object>> checkFeature(
            @PathVariable String deviceId, @PathVariable String sessionId,
            @RequestParam String feature) {
        boolean allowed = guestModeService.isFeatureAllowed(sessionId, feature);
        return ApiResponse.ok(Map.of("session_id", sessionId, "feature", feature, "allowed", allowed));
    }
}
