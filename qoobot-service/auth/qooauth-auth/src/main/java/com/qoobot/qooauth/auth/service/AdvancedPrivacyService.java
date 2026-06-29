package com.qoobot.qooauth.auth.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Advanced Privacy Service.
 *
 * Implements advanced privacy-preserving techniques:
 * - ATT Tracking Transparency (cross-app tracking authorization)
 * - Differential Privacy (data collection with noise)
 * - Anonymization (k-anonymity, data masking, irreversible hashing)
 * - Local Processing Priority (sensitive data stays on-device)
 */
@Service
public class AdvancedPrivacyService {
    private static final Logger log = LoggerFactory.getLogger(AdvancedPrivacyService.class);

    private final SecureRandom secureRandom = new SecureRandom();

    // ============================================================
    //  ATT Tracking Transparency
    // ============================================================

    /**
     * In-memory tracking authorization store.
     * In production, this would be persisted to PostgreSQL.
     * Key: userId, Value: tracking authorization state
     */
    private final ConcurrentHashMap<String, TrackingAuthorization> trackingAuthStore = new ConcurrentHashMap<>();

    /**
     * Request tracking authorization from a user (IDFA-style).
     * Returns an authorization token that apps can check.
     */
    public TrackingAuthorization requestTrackingAuthorization(String userId, String appId,
                                                                String purpose) {
        TrackingAuthorization auth = new TrackingAuthorization();
        auth.userId = userId;
        auth.appId = appId;
        auth.purpose = purpose;
        auth.authorizationToken = generateTrackingToken();
        auth.status = "PENDING";
        auth.requestedAt = System.currentTimeMillis();

        trackingAuthStore.put(userId + ":" + appId, auth);
        log.info("Tracking authorization requested for user {} by app {}: {}",
                userId, appId, purpose);
        return auth;
    }

    /**
     * User grants or denies tracking authorization.
     */
    public TrackingAuthorization decideTracking(String userId, String appId,
                                                  boolean allowed) {
        TrackingAuthorization auth = trackingAuthStore.get(userId + ":" + appId);
        if (auth == null) {
            throw new IllegalArgumentException("No pending tracking request for this user/app");
        }

        auth.status = allowed ? "AUTHORIZED" : "DENIED";
        auth.decidedAt = System.currentTimeMillis();
        trackingAuthStore.put(userId + ":" + appId, auth);

        log.info("Tracking authorization for user {} app {}: {}", userId, appId, auth.status);
        return auth;
    }

    /**
     * Check if an app is authorized to track a user.
     */
    public boolean isTrackingAuthorized(String userId, String appId) {
        TrackingAuthorization auth = trackingAuthStore.get(userId + ":" + appId);
        return auth != null && "AUTHORIZED".equals(auth.status);
    }

    /**
     * Generate a privacy-safe advertising identifier (rotation-capable).
     * Users can rotate their identifier at any time, and apps get
     * zeroes if tracking is denied.
     */
    public String getAdvertisingIdentifier(String userId, String appId, boolean trackingAllowed) {
        if (!trackingAllowed || !isTrackingAuthorized(userId, appId)) {
            // Return all-zero identifier — privacy-preserving default
            return "00000000-0000-0000-0000-000000000000";
        }
        // Generate a stable identifier per user-app pair
        return generateStableIdentifier(userId, appId);
    }

    // ============================================================
    //  Differential Privacy
    // ============================================================

    /**
     * Default privacy budget per user per day (epsilon).
     * Exceeding this budget triggers data collection throttling.
     */
    private static final double DEFAULT_EPSILON_BUDGET = 1.0;
    private static final double DEFAULT_EPSILON_PER_QUERY = 0.1;

    private final ConcurrentHashMap<String, PrivacyBudget> privacyBudgets = new ConcurrentHashMap<>();

    /**
     * Apply Laplace noise to a numeric value for differential privacy.
     *
     * @param value The raw numeric value to protect
     * @param sensitivity The sensitivity of the query (max change from one record)
     * @param epsilon Privacy parameter (lower = more privacy, more noise)
     * @return Noisy value with Laplace noise applied
     */
    public double applyLaplaceNoise(double value, double sensitivity, double epsilon) {
        double noise = laplaceRandom(sensitivity / epsilon);
        return value + noise;
    }

    /**
     * Apply Gaussian noise (for (ε, δ)-differential privacy).
     */
    public double applyGaussianNoise(double value, double sensitivity,
                                      double epsilon, double delta) {
        double sigma = (sensitivity / epsilon) * Math.sqrt(2 * Math.log(1.25 / delta));
        double noise = gaussianRandom(sigma);
        return value + noise;
    }

    /**
     * Check and consume privacy budget for a query.
     * Returns true if the query can proceed within budget.
     */
    public boolean consumePrivacyBudget(String datasetId, double epsilonCost) {
        String key = datasetId + ":" + getCurrentDayKey();
        PrivacyBudget budget = privacyBudgets.computeIfAbsent(key,
                k -> new PrivacyBudget(DEFAULT_EPSILON_BUDGET));

        if (budget.remainingBudget >= epsilonCost) {
            budget.remainingBudget -= epsilonCost;
            budget.queryCount++;
            return true;
        }

        log.warn("Privacy budget exceeded for dataset {}: {}/{}",
                datasetId, budget.remainingBudget, DEFAULT_EPSILON_BUDGET);
        return false;
    }

    /**
     * Get current privacy budget status.
     */
    public PrivacyBudget getPrivacyBudget(String datasetId) {
        return privacyBudgets.getOrDefault(datasetId + ":" + getCurrentDayKey(),
                new PrivacyBudget(DEFAULT_EPSILON_BUDGET));
    }

    /**
     * Randomized response for binary survey questions (local DP).
     * User flips a coin: heads = truth, tails = random answer.
     * This provides plausible deniability at the individual level
     * while allowing aggregate statistics.
     */
    public boolean randomizedResponse(boolean trueAnswer, double privacyProbability) {
        double coin = secureRandom.nextDouble();
        if (coin < privacyProbability) {
            // Tell the truth
            return trueAnswer;
        } else if (coin < privacyProbability + (1 - privacyProbability) / 2) {
            // Random yes
            return true;
        } else {
            // Random no
            return false;
        }
    }

    // ============================================================
    //  Anonymization (k-Anonymity & Data Masking)
    // ============================================================

    /**
     * Apply k-anonymity: suppress values that would make groups smaller than k.
     *
     * @param records List of records with quasi-identifier values
     * @param k Minimum group size
     * @return Anonymized records with suppressed quasi-identifiers
     */
    public List<Map<String, Object>> applyKAnonymity(List<Map<String, Object>> records,
                                                       List<String> quasiIdentifiers, int k) {
        // Group records by quasi-identifier combinations
        Map<String, List<Map<String, Object>>> groups = new LinkedHashMap<>();
        for (var record : records) {
            String key = buildQuasiKey(record, quasiIdentifiers);
            groups.computeIfAbsent(key, x -> new ArrayList<>()).add(record);
        }

        // Suppress quasi-identifiers for groups smaller than k
        List<Map<String, Object>> result = new ArrayList<>();
        for (var entry : groups.entrySet()) {
            if (entry.getValue().size() < k) {
                // Suppress: generalize quasi-identifiers
                for (var record : entry.getValue()) {
                    Map<String, Object> suppressed = new LinkedHashMap<>(record);
                    for (String qi : quasiIdentifiers) {
                        suppressed.put(qi, generalizeValue(record.get(qi)));
                    }
                    result.add(suppressed);
                }
            } else {
                result.addAll(entry.getValue());
            }
        }

        log.debug("k-anonymity applied: {} records, {} groups, k={}",
                records.size(), groups.size(), k);
        return result;
    }

    /**
     * Mask sensitive data fields with irreversible hashing.
     * Uses SHA-256 with per-record salt for one-way anonymization.
     */
    public String maskWithHash(String value, String salt) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            md.update(salt.getBytes());
            byte[] hash = md.digest(value.getBytes());
            return Base64.getUrlEncoder().withoutPadding().encodeToString(hash);
        } catch (Exception e) {
            log.error("Hash masking failed", e);
            return "MASKED";
        }
    }

    /**
     * Mask PII (Personally Identifiable Information) in a data record.
     * Supports: email, phone, name, address, SSN masking patterns.
     */
    public String maskPii(String value, String piiType) {
        if (value == null || value.isEmpty()) return value;

        return switch (piiType.toUpperCase()) {
            case "EMAIL" -> maskEmail(value);
            case "PHONE" -> maskPhone(value);
            case "NAME" -> maskName(value);
            case "ADDRESS" -> maskAddress(value);
            case "SSN", "ID_CARD" -> maskIdNumber(value);
            case "IP" -> maskIpAddress(value);
            default -> maskGeneric(value);
        };
    }

    /**
     * Apply differential privacy to a count query (e.g., "how many users have X?").
     * Uses the Laplace mechanism.
     */
    public long privatizeCount(long trueCount, double epsilon) {
        double noise = laplaceRandom(1.0 / epsilon);
        return Math.max(0, Math.round(trueCount + noise));
    }

    // ============================================================
    //  Local Processing Priority
    // ============================================================

    /**
     * Data processing tier: LOCAL_ONLY, LOCAL_PREFERRED, CLOUD_ALLOWED
     */
    public enum ProcessingTier {
        LOCAL_ONLY,      // Must stay on device, never uploaded
        LOCAL_PREFERRED, // Process locally, upload only with explicit consent
        CLOUD_ALLOWED    // Can be processed in cloud
    }

    /**
     * Mapping of data types to their required processing tier.
     */
    private static final Map<String, ProcessingTier> DATA_PROCESSING_TIERS = Map.of(
            "biometric_template", ProcessingTier.LOCAL_ONLY,
            "health_data", ProcessingTier.LOCAL_ONLY,
            "raw_audio", ProcessingTier.LOCAL_PREFERRED,
            "raw_video", ProcessingTier.LOCAL_PREFERRED,
            "location_history", ProcessingTier.LOCAL_PREFERRED,
            "personal_contacts", ProcessingTier.LOCAL_ONLY,
            "device_telemetry", ProcessingTier.CLOUD_ALLOWED,
            "anonymized_analytics", ProcessingTier.CLOUD_ALLOWED,
            "skill_usage_stats", ProcessingTier.CLOUD_ALLOWED
    );

    /**
     * Determine if a data type can be uploaded to cloud.
     */
    public boolean canUploadToCloud(String dataType, boolean userConsentGiven) {
        ProcessingTier tier = DATA_PROCESSING_TIERS.getOrDefault(
                dataType, ProcessingTier.LOCAL_PREFERRED);

        return switch (tier) {
            case LOCAL_ONLY -> false;
            case LOCAL_PREFERRED -> userConsentGiven;
            case CLOUD_ALLOWED -> true;
        };
    }

    /**
     * Get the processing tier for a data type.
     */
    public ProcessingTier getProcessingTier(String dataType) {
        return DATA_PROCESSING_TIERS.getOrDefault(dataType, ProcessingTier.LOCAL_PREFERRED);
    }

    /**
     * Generate a selective sync plan: which data should stay local vs. cloud.
     */
    public SyncPlan generateSyncPlan(Map<String, Long> dataSizes,
                                       Map<String, Boolean> userConsents) {
        SyncPlan plan = new SyncPlan();
        plan.localData = new LinkedHashMap<>();
        plan.cloudData = new LinkedHashMap<>();

        for (var entry : dataSizes.entrySet()) {
            String dataType = entry.getKey();
            long size = entry.getValue();
            boolean consent = userConsents.getOrDefault(dataType, false);

            if (canUploadToCloud(dataType, consent)) {
                plan.cloudData.put(dataType, size);
            } else {
                plan.localData.put(dataType, size);
            }
        }

        plan.totalLocalBytes = plan.localData.values().stream().mapToLong(Long::longValue).sum();
        plan.totalCloudBytes = plan.cloudData.values().stream().mapToLong(Long::longValue).sum();

        return plan;
    }

    // ============================================================
    //  Helper Methods
    // ============================================================

    private String generateTrackingToken() {
        byte[] bytes = new byte[16];
        secureRandom.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private String generateStableIdentifier(String userId, String appId) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            md.update(userId.getBytes());
            md.update(":".getBytes());
            md.update(appId.getBytes());
            byte[] hash = md.digest();
            // Format as UUID-like string
            return String.format("%08x-%04x-%04x-%04x-%012x",
                    ((hash[0] & 0xff) << 24) | ((hash[1] & 0xff) << 16) | ((hash[2] & 0xff) << 8) | (hash[3] & 0xff),
                    ((hash[4] & 0xff) << 8) | (hash[5] & 0xff),
                    ((hash[6] & 0xff) << 8) | (hash[7] & 0xff),
                    ((hash[8] & 0xff) << 8) | (hash[9] & 0xff),
                    ((long)(hash[10] & 0xff) << 40) | ((long)(hash[11] & 0xff) << 32) |
                    ((long)(hash[12] & 0xff) << 24) | ((hash[13] & 0xff) << 16) |
                    ((hash[14] & 0xff) << 8) | (hash[15] & 0xff));
        } catch (Exception e) {
            return "00000000-0000-0000-0000-000000000000";
        }
    }

    private double laplaceRandom(double scale) {
        double u = secureRandom.nextDouble() - 0.5;
        return -scale * Math.signum(u) * Math.log(1 - 2 * Math.abs(u));
    }

    private double gaussianRandom(double sigma) {
        return secureRandom.nextGaussian() * sigma;
    }

    private String getCurrentDayKey() {
        return java.time.LocalDate.now().toString();
    }

    private String buildQuasiKey(Map<String, Object> record, List<String> identifiers) {
        StringBuilder sb = new StringBuilder();
        for (String qi : identifiers) {
            sb.append(record.getOrDefault(qi, "*")).append("|");
        }
        return sb.toString();
    }

    private Object generalizeValue(Object value) {
        if (value == null) return "*";
        String s = value.toString();
        if (s.length() <= 2) return "*";
        // Generalize: keep first character, mask rest
        return s.charAt(0) + "*".repeat(Math.min(s.length() - 1, 3));
    }

    private String maskEmail(String email) {
        int atIndex = email.indexOf('@');
        if (atIndex <= 1) return "***@" + email.substring(atIndex + 1);
        return email.charAt(0) + "***" + email.substring(atIndex);
    }

    private String maskPhone(String phone) {
        if (phone.length() <= 4) return "****";
        return phone.substring(0, Math.min(3, phone.length() - 4)) + "****" +
                phone.substring(Math.max(phone.length() - 4, 3));
    }

    private String maskName(String name) {
        if (name.length() <= 1) return "*";
        return name.charAt(0) + "*".repeat(name.length() - 1);
    }

    private String maskAddress(String address) {
        // Keep city/state, mask street number
        return "[REDACTED_ADDRESS]";
    }

    private String maskIdNumber(String id) {
        if (id.length() <= 4) return "****";
        return "****" + id.substring(id.length() - 4);
    }

    private String maskIpAddress(String ip) {
        int lastDot = ip.lastIndexOf('.');
        if (lastDot > 0) {
            return ip.substring(0, lastDot) + ".0";
        }
        return "0.0.0.0";
    }

    private String maskGeneric(String value) {
        if (value.length() <= 4) return "****";
        return value.substring(0, 2) + "****" + value.substring(value.length() - 2);
    }

    // ============================================================
    //  DTOs
    // ============================================================

    public static class TrackingAuthorization {
        public String userId;
        public String appId;
        public String purpose;
        public String authorizationToken;
        public String status; // PENDING, AUTHORIZED, DENIED
        public long requestedAt;
        public long decidedAt;

        public Map<String, Object> toMap() {
            return Map.of(
                    "user_id", userId,
                    "app_id", appId,
                    "purpose", purpose,
                    "status", status,
                    "authorization_token", authorizationToken,
                    "requested_at", requestedAt,
                    "decided_at", decidedAt
            );
        }
    }

    public static class PrivacyBudget {
        public double totalBudget;
        public double remainingBudget;
        public int queryCount;

        public PrivacyBudget(double totalBudget) {
            this.totalBudget = totalBudget;
            this.remainingBudget = totalBudget;
            this.queryCount = 0;
        }

        public Map<String, Object> toMap() {
            return Map.of(
                    "total_budget", totalBudget,
                    "remaining_budget", Math.max(0, remainingBudget),
                    "consumed_budget", totalBudget - remainingBudget,
                    "query_count", queryCount
            );
        }
    }

    public static class SyncPlan {
        public Map<String, Long> localData;
        public Map<String, Long> cloudData;
        public long totalLocalBytes;
        public long totalCloudBytes;

        public Map<String, Object> toMap() {
            return Map.of(
                    "local_data", localData,
                    "cloud_data", cloudData,
                    "total_local_bytes", totalLocalBytes,
                    "total_cloud_bytes", totalCloudBytes,
                    "recommendation", totalLocalBytes > totalCloudBytes ?
                            "Prefer local processing for sensitive data" :
                            "Cloud sync available for most data types"
            );
        }
    }
}
