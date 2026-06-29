package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.service.AdvancedPrivacyService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST controller for advanced privacy operations:
 * ATT Tracking Transparency, Differential Privacy, Anonymization, Local Processing.
 */
@RestController
@RequestMapping("/api/v1/auth/privacy/advanced")
public class AdvancedPrivacyController {

    private final AdvancedPrivacyService privacyService;

    public AdvancedPrivacyController(AdvancedPrivacyService privacyService) {
        this.privacyService = privacyService;
    }

    // ---- ATT Tracking Transparency ----

    /**
     * Request tracking authorization for an app.
     */
    @PostMapping("/tracking/request")
    public ResponseEntity<Map<String, Object>> requestTracking(@RequestBody Map<String, String> request) {
        String userId = request.get("user_id");
        String appId = request.get("app_id");
        String purpose = request.getOrDefault("purpose", "personalized_experience");

        AdvancedPrivacyService.TrackingAuthorization auth =
                privacyService.requestTrackingAuthorization(userId, appId, purpose);

        return ResponseEntity.ok(auth.toMap());
    }

    /**
     * User decides on tracking authorization.
     */
    @PostMapping("/tracking/decide")
    public ResponseEntity<Map<String, Object>> decideTracking(@RequestBody Map<String, Object> request) {
        String userId = (String) request.get("user_id");
        String appId = (String) request.get("app_id");
        boolean allowed = (Boolean) request.getOrDefault("allowed", false);

        AdvancedPrivacyService.TrackingAuthorization auth =
                privacyService.decideTracking(userId, appId, allowed);

        return ResponseEntity.ok(auth.toMap());
    }

    /**
     * Check tracking authorization status.
     */
    @GetMapping("/tracking/status")
    public ResponseEntity<Map<String, Object>> trackingStatus(
            @RequestParam String userId, @RequestParam String appId) {
        boolean authorized = privacyService.isTrackingAuthorized(userId, appId);
        return ResponseEntity.ok(Map.of("tracking_authorized", authorized));
    }

    /**
     * Get privacy-safe advertising identifier.
     */
    @GetMapping("/tracking/advertising-id")
    public ResponseEntity<Map<String, Object>> getAdvertisingId(
            @RequestParam String userId, @RequestParam String appId,
            @RequestParam(defaultValue = "false") boolean trackingAllowed) {
        String id = privacyService.getAdvertisingIdentifier(userId, appId, trackingAllowed);
        return ResponseEntity.ok(Map.of("advertising_identifier", id));
    }

    // ---- Differential Privacy ----

    /**
     * Apply Laplace noise to a numeric value.
     */
    @PostMapping("/dp/laplace")
    public ResponseEntity<Map<String, Object>> applyLaplace(@RequestBody Map<String, Object> request) {
        double value = ((Number) request.get("value")).doubleValue();
        double sensitivity = ((Number) request.getOrDefault("sensitivity", 1.0)).doubleValue();
        double epsilon = ((Number) request.getOrDefault("epsilon", 0.1)).doubleValue();

        double noisy = privacyService.applyLaplaceNoise(value, sensitivity, epsilon);
        return ResponseEntity.ok(Map.of("noisy_value", noisy, "original_value", value,
                "noise_added", noisy - value));
    }

    /**
     * Apply Gaussian noise for (ε, δ)-DP.
     */
    @PostMapping("/dp/gaussian")
    public ResponseEntity<Map<String, Object>> applyGaussian(@RequestBody Map<String, Object> request) {
        double value = ((Number) request.get("value")).doubleValue();
        double sensitivity = ((Number) request.getOrDefault("sensitivity", 1.0)).doubleValue();
        double epsilon = ((Number) request.getOrDefault("epsilon", 0.1)).doubleValue();
        double delta = ((Number) request.getOrDefault("delta", 1e-5)).doubleValue();

        double noisy = privacyService.applyGaussianNoise(value, sensitivity, epsilon, delta);
        return ResponseEntity.ok(Map.of("noisy_value", noisy, "epsilon", epsilon, "delta", delta));
    }

    /**
     * Get privacy budget status.
     */
    @GetMapping("/dp/budget/{datasetId}")
    public ResponseEntity<Map<String, Object>> getBudget(@PathVariable String datasetId) {
        AdvancedPrivacyService.PrivacyBudget budget = privacyService.getPrivacyBudget(datasetId);
        return ResponseEntity.ok(budget.toMap());
    }

    /**
     * Consume privacy budget for a query.
     */
    @PostMapping("/dp/consume-budget")
    public ResponseEntity<Map<String, Object>> consumeBudget(@RequestBody Map<String, Object> request) {
        String datasetId = (String) request.get("dataset_id");
        double epsilonCost = ((Number) request.getOrDefault("epsilon_cost", 0.1)).doubleValue();

        boolean allowed = privacyService.consumePrivacyBudget(datasetId, epsilonCost);
        return ResponseEntity.ok(Map.of("allowed", allowed, "dataset_id", datasetId,
                "epsilon_cost", epsilonCost));
    }

    /**
     * Privatize a count query with DP.
     */
    @PostMapping("/dp/privatize-count")
    public ResponseEntity<Map<String, Object>> privatizeCount(@RequestBody Map<String, Object> request) {
        long trueCount = ((Number) request.get("true_count")).longValue();
        double epsilon = ((Number) request.getOrDefault("epsilon", 0.1)).doubleValue();

        long privatized = privacyService.privatizeCount(trueCount, epsilon);
        return ResponseEntity.ok(Map.of("privatized_count", privatized,
                "true_count", trueCount, "epsilon", epsilon));
    }

    // ---- Anonymization ----

    /**
     * Apply k-anonymity to a dataset.
     */
    @PostMapping("/anonymize/k-anonymity")
    public ResponseEntity<Map<String, Object>> kAnonymize(@RequestBody Map<String, Object> request) {
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> records = (List<Map<String, Object>>) request.get("records");

        @SuppressWarnings("unchecked")
        List<String> quasiIds = (List<String>) request.get("quasi_identifiers");

        int k = ((Number) request.getOrDefault("k", 5)).intValue();

        List<Map<String, Object>> result = privacyService.applyKAnonymity(records, quasiIds, k);
        return ResponseEntity.ok(Map.of("anonymized_records", result, "k", k,
                "original_count", records.size(), "anonymized_count", result.size()));
    }

    /**
     * Mask PII in a value.
     */
    @PostMapping("/anonymize/mask-pii")
    public ResponseEntity<Map<String, Object>> maskPii(@RequestBody Map<String, String> request) {
        String value = request.get("value");
        String piiType = request.getOrDefault("pii_type", "GENERIC");

        String masked = privacyService.maskPii(value, piiType);
        return ResponseEntity.ok(Map.of("masked_value", masked, "pii_type", piiType));
    }

    /**
     * Hash-mask a value with salt.
     */
    @PostMapping("/anonymize/hash-mask")
    public ResponseEntity<Map<String, Object>> hashMask(@RequestBody Map<String, String> request) {
        String value = request.get("value");
        String salt = request.getOrDefault("salt", "default_salt");

        String masked = privacyService.maskWithHash(value, salt);
        return ResponseEntity.ok(Map.of("hashed_value", masked));
    }

    // ---- Local Processing Priority ----

    /**
     * Check if a data type can be uploaded to cloud.
     */
    @GetMapping("/local-processing/can-upload")
    public ResponseEntity<Map<String, Object>> canUpload(
            @RequestParam String dataType,
            @RequestParam(defaultValue = "false") boolean userConsent) {
        boolean canUpload = privacyService.canUploadToCloud(dataType, userConsent);
        AdvancedPrivacyService.ProcessingTier tier = privacyService.getProcessingTier(dataType);

        return ResponseEntity.ok(Map.of(
                "data_type", dataType,
                "can_upload_to_cloud", canUpload,
                "processing_tier", tier.name(),
                "user_consent_given", userConsent
        ));
    }

    /**
     * Generate a selective sync plan.
     */
    @PostMapping("/local-processing/sync-plan")
    public ResponseEntity<Map<String, Object>> syncPlan(@RequestBody Map<String, Object> request) {
        @SuppressWarnings("unchecked")
        Map<String, Object> sizes = (Map<String, Object>) request.get("data_sizes");
        @SuppressWarnings("unchecked")
        Map<String, Object> consents = (Map<String, Object>) request.getOrDefault("user_consents", Map.of());

        Map<String, Long> dataSizes = new java.util.LinkedHashMap<>();
        for (var entry : sizes.entrySet()) {
            dataSizes.put(entry.getKey(), ((Number) entry.getValue()).longValue());
        }

        Map<String, Boolean> userConsents = new java.util.LinkedHashMap<>();
        for (var entry : consents.entrySet()) {
            userConsents.put(entry.getKey(), (Boolean) entry.getValue());
        }

        AdvancedPrivacyService.SyncPlan plan = privacyService.generateSyncPlan(dataSizes, userConsents);
        return ResponseEntity.ok(plan.toMap());
    }
}
