package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.entity.ConsentRecord;
import com.qoobot.qooauth.auth.service.PrivacyConsentService;
import com.qoobot.qooauth.auth.service.PrivacyConsentService.PrivacyLabel;
import com.qoobot.qooauth.common.dto.ApiResponse;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Privacy & Consent Controller.
 * <p>
 * Endpoints for:
 * <ul>
 *   <li>Consent management (grant/withdraw/check)</li>
 *   <li>Privacy labels (transparency)</li>
 *   <li>Data portability (GDPR export)</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/v1/auth/privacy")
public class PrivacyConsentController {

    private final PrivacyConsentService privacyConsentService;

    public PrivacyConsentController(PrivacyConsentService privacyConsentService) {
        this.privacyConsentService = privacyConsentService;
    }

    /**
     * Get all privacy labels (public transparency).
     */
    @GetMapping("/labels")
    public ApiResponse<Map<String, PrivacyLabel>> getPrivacyLabels() {
        return ApiResponse.ok(privacyConsentService.getAllPrivacyLabels());
    }

    /**
     * Get privacy label for a specific data type.
     */
    @GetMapping("/labels/{dataType}")
    public ApiResponse<PrivacyLabel> getPrivacyLabel(@PathVariable String dataType) {
        PrivacyLabel label = privacyConsentService.getPrivacyLabel(dataType);
        return ApiResponse.ok(label);
    }

    /**
     * Grant consent for a data processing purpose.
     */
    @PostMapping("/consent/grant")
    public ApiResponse<ConsentRecord> grantConsent(@RequestBody Map<String, String> body,
                                                    @RequestHeader(value = "X-Forwarded-For", required = false) String forwardedFor,
                                                    @RequestHeader(value = "User-Agent", required = false) String userAgent,
                                                    jakarta.servlet.http.HttpServletRequest request) {
        String userId = body.get("user_id");
        String purpose = body.get("purpose");
        String consentVersion = body.getOrDefault("consent_version", "1.0");
        String privacyPolicyVersion = body.getOrDefault("privacy_policy_version", "1.0");
        String ip = forwardedFor != null ? forwardedFor.split(",")[0].trim() : request.getRemoteAddr();

        ConsentRecord record = privacyConsentService.recordConsent(
                userId, purpose, true, ip, userAgent,
                consentVersion, privacyPolicyVersion);
        return ApiResponse.ok(record);
    }

    /**
     * Withdraw consent for a purpose.
     */
    @PostMapping("/consent/withdraw")
    public ApiResponse<Map<String, String>> withdrawConsent(@RequestBody Map<String, String> body) {
        String userId = body.get("user_id");
        String purpose = body.get("purpose");

        privacyConsentService.withdrawConsent(userId, purpose);

        Map<String, String> result = new HashMap<>();
        result.put("user_id", userId);
        result.put("purpose", purpose);
        result.put("status", "withdrawn");
        return ApiResponse.ok(result);
    }

    /**
     * Check if user has granted consent for a purpose.
     */
    @GetMapping("/consent/check")
    public ApiResponse<Map<String, Object>> checkConsent(
            @RequestParam String userId, @RequestParam String purpose) {
        boolean granted = privacyConsentService.hasConsent(userId, purpose);
        return ApiResponse.ok(Map.of("user_id", userId, "purpose", purpose, "granted", granted));
    }

    /**
     * Get all active consents for a user.
     */
    @GetMapping("/consent/{userId}")
    public ApiResponse<List<ConsentRecord>> getActiveConsents(@PathVariable String userId) {
        List<ConsentRecord> consents = privacyConsentService.getActiveConsents(userId);
        return ApiResponse.ok(consents);
    }

    /**
     * Get full consent history for a user.
     */
    @GetMapping("/consent/{userId}/history")
    public ApiResponse<List<ConsentRecord>> getConsentHistory(@PathVariable String userId) {
        List<ConsentRecord> history = privacyConsentService.getConsentHistory(userId);
        return ApiResponse.ok(history);
    }

    /**
     * Generate GDPR data portability export.
     */
    @GetMapping("/export/{userId}")
    public ApiResponse<Map<String, Object>> exportData(@PathVariable String userId) {
        Map<String, Object> export = privacyConsentService.generateDataExport(userId);
        return ApiResponse.ok(export);
    }

    /**
     * Revoke all consents for a user (e.g., on account deletion).
     */
    @PostMapping("/consent/revoke-all")
    public ApiResponse<Map<String, String>> revokeAllConsents(@RequestBody Map<String, String> body) {
        String userId = body.get("user_id");
        privacyConsentService.revokeAllConsents(userId);
        return ApiResponse.ok(Map.of("user_id", userId, "status", "all_consents_revoked"));
    }
}
