package com.qoobot.qooauth.auth.service;

import com.qoobot.qooauth.auth.entity.ApiKey;
import com.qoobot.qooauth.auth.entity.ApiKeyUsage;
import com.qoobot.qooauth.auth.repository.ApiKeyRepository;
import com.qoobot.qooauth.auth.repository.ApiKeyUsageRepository;
import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.common.util.IdGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Base64;
import java.util.HexFormat;
import java.util.List;
import java.util.Optional;

/**
 * API Key lifecycle management service.
 * Handles key generation, rotation, revocation, permission binding, and usage quotas.
 *
 * Key format: qk_ + 40 random URL-safe chars (52 chars total)
 * Storage: only SHA-256 hash is stored; the raw key is shown once at creation.
 */
@Service
public class ApiKeyService {

    private static final Logger log = LoggerFactory.getLogger(ApiKeyService.class);
    private static final SecureRandom SECURE_RANDOM = new SecureRandom();
    private static final int KEY_RANDOM_BYTES = 30; // 30 bytes -> 40 Base64URL chars
    private static final int MAX_KEYS_PER_USER = 20;
    private static final int KEY_PREFIX_LENGTH = 12; // "qk_" + 8 chars

    private final ApiKeyRepository apiKeyRepository;
    private final ApiKeyUsageRepository apiKeyUsageRepository;

    public ApiKeyService(ApiKeyRepository apiKeyRepository,
                         ApiKeyUsageRepository apiKeyUsageRepository) {
        this.apiKeyRepository = apiKeyRepository;
        this.apiKeyUsageRepository = apiKeyUsageRepository;
    }

    /**
     * Create a new API key for a user.
     *
     * @param userId      Owner user ID
     * @param keyName     Human-readable name
     * @param keyType     "API", "ROBOT", or "DEVELOPER"
     * @param scopes      JSON array of OAuth-style scopes
     * @param resourceIds JSON array of resource access paths
     * @param rateLimit   Requests per hour (default 1000)
     * @param quotaLimit  Requests per month (default 10000)
     * @param expiresInDays Days until expiry (null = no expiry)
     * @return The created key info including the raw key (shown only once)
     */
    @Transactional
    public ApiKeyCreationResult createKey(String userId, String keyName, String keyType,
                                          String scopes, String resourceIds,
                                          Integer rateLimit, Integer quotaLimit,
                                          Integer expiresInDays) {
        // Check maximum keys per user
        long activeCount = apiKeyRepository.countByUserIdAndState(userId, "ACTIVE");
        if (activeCount >= MAX_KEYS_PER_USER) {
            throw new AuthException(ErrorCodes.API_KEY_LIMIT_EXCEEDED,
                    "Maximum " + MAX_KEYS_PER_USER + " active API keys allowed per user");
        }

        // Generate raw key
        String rawKey = generateRawKey();
        String keyHash = sha256(rawKey);
        String keyPrefix = rawKey.substring(0, KEY_PREFIX_LENGTH);

        // Build entity
        ApiKey apiKey = new ApiKey();
        apiKey.setKeyId(IdGenerator.generateApiKeyId());
        apiKey.setUserId(userId);
        apiKey.setKeyName(keyName);
        apiKey.setKeyPrefix(keyPrefix);
        apiKey.setKeyHash(keyHash);
        apiKey.setKeyType(keyType != null ? keyType : "API");
        apiKey.setState("ACTIVE");
        apiKey.setScopes(scopes != null ? scopes : "[\"openid\",\"profile\",\"email\"]");
        apiKey.setResourceIds(resourceIds);
        apiKey.setRateLimit(rateLimit != null ? rateLimit : 1000);
        apiKey.setQuotaLimit(quotaLimit != null ? quotaLimit : 10000);
        apiKey.setQuotaUsed(0);
        apiKey.setQuotaResetAt(Instant.now().truncatedTo(ChronoUnit.DAYS)
                .plus(30 - Instant.now().atZone(java.time.ZoneId.systemDefault()).getDayOfMonth() + 1,
                        ChronoUnit.DAYS));
        apiKey.setCreatedAt(Instant.now());

        if (expiresInDays != null && expiresInDays > 0) {
            apiKey.setExpiresAt(Instant.now().plus(expiresInDays, ChronoUnit.DAYS));
        }

        apiKey = apiKeyRepository.save(apiKey);

        log.info("API key created: keyId={}, userId={}, keyName={}", apiKey.getKeyId(), userId, keyName);

        return new ApiKeyCreationResult(
                apiKey.getKeyId(), apiKey.getKeyName(), rawKey, apiKey.getKeyPrefix(),
                apiKey.getKeyType(), apiKey.getScopes(), apiKey.getRateLimit(),
                apiKey.getQuotaLimit(), apiKey.getExpiresAt(), apiKey.getCreatedAt()
        );
    }

    /**
     * List all API keys for a user.
     */
    public List<ApiKey> listKeys(String userId) {
        return apiKeyRepository.findByUserId(userId);
    }

    /**
     * Get a single API key by ID (must belong to the user).
     */
    public ApiKey getKey(String userId, String keyId) {
        ApiKey key = apiKeyRepository.findById(keyId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "API key not found"));
        if (!key.getUserId().equals(userId)) {
            throw new AuthException(ErrorCodes.INSUFFICIENT_PERMISSIONS, "Access denied");
        }
        return key;
    }

    /**
     * Revoke an API key.
     */
    @Transactional
    public void revokeKey(String userId, String keyId, String reason) {
        ApiKey key = getKey(userId, keyId);
        if (!"ACTIVE".equals(key.getState())) {
            throw new AuthException(ErrorCodes.API_KEY_ALREADY_REVOKED,
                    "API key is already " + key.getState().toLowerCase());
        }
        key.setState("REVOKED");
        key.setRevokedAt(Instant.now());
        key.setRevokedReason(reason);
        apiKeyRepository.save(key);

        log.info("API key revoked: keyId={}, userId={}, reason={}", keyId, userId, reason);
    }

    /**
     * Rotate an API key: revoke old, create new with same configuration.
     * Returns the new raw key.
     */
    @Transactional
    public ApiKeyCreationResult rotateKey(String userId, String keyId) {
        ApiKey oldKey = getKey(userId, keyId);
        if (!"ACTIVE".equals(oldKey.getState())) {
            throw new AuthException(ErrorCodes.API_KEY_ALREADY_REVOKED,
                    "Cannot rotate a " + oldKey.getState().toLowerCase() + " key");
        }

        // Calculate remaining expiry days
        Integer expiresInDays = null;
        if (oldKey.getExpiresAt() != null) {
            long days = ChronoUnit.DAYS.between(Instant.now(), oldKey.getExpiresAt());
            expiresInDays = (int) Math.max(1, days);
        }

        // Revoke old key
        oldKey.setState("REVOKED");
        oldKey.setRevokedAt(Instant.now());
        oldKey.setRevokedReason("Key rotation");
        apiKeyRepository.save(oldKey);

        // Create new key with same configuration
        return createKey(userId, oldKey.getKeyName() + " (rotated)", oldKey.getKeyType(),
                oldKey.getScopes(), oldKey.getResourceIds(),
                oldKey.getRateLimit(), oldKey.getQuotaLimit(), expiresInDays);
    }

    /**
     * Validate an API key by its raw value.
     * Returns the ApiKey entity if valid, throws otherwise.
     */
    @Transactional
    public ApiKey validateKey(String rawKey) {
        String keyHash = sha256(rawKey);

        ApiKey key = apiKeyRepository.findByKeyHash(keyHash)
                .orElseThrow(() -> new AuthException(ErrorCodes.INVALID_API_KEY, "Invalid API key"));

        if ("REVOKED".equals(key.getState())) {
            throw new AuthException(ErrorCodes.API_KEY_REVOKED, "API key has been revoked");
        }

        if ("EXPIRED".equals(key.getState())) {
            throw new AuthException(ErrorCodes.API_KEY_EXPIRED, "API key has expired");
        }

        if (key.getExpiresAt() != null && key.getExpiresAt().isBefore(Instant.now())) {
            key.setState("EXPIRED");
            apiKeyRepository.save(key);
            throw new AuthException(ErrorCodes.API_KEY_EXPIRED, "API key has expired");
        }

        // Check monthly quota
        if (key.getQuotaResetAt().isBefore(Instant.now())) {
            // Reset quota for new month
            key.setQuotaUsed(0);
            key.setQuotaResetAt(Instant.now().truncatedTo(ChronoUnit.DAYS)
                    .plus(30 - Instant.now().atZone(java.time.ZoneId.systemDefault()).getDayOfMonth() + 1,
                            ChronoUnit.DAYS));
        }

        if (key.getQuotaUsed() >= key.getQuotaLimit()) {
            throw new AuthException(ErrorCodes.API_KEY_QUOTA_EXCEEDED,
                    "API key monthly quota exceeded (" + key.getQuotaLimit() + " requests)");
        }

        // Increment usage counter
        apiKeyRepository.incrementQuotaUsed(key.getKeyId(), Instant.now());

        return key;
    }

    /**
     * Record an API key usage event for audit and quota tracking.
     */
    @Transactional
    public void recordUsage(String keyId, String endpoint, String method,
                            int statusCode, Integer durationMs,
                            String ipAddress, String userAgent) {
        ApiKeyUsage usage = new ApiKeyUsage();
        usage.setUsageId(IdGenerator.generateApiKeyUsageId());
        usage.setKeyId(keyId);
        usage.setEndpoint(endpoint);
        usage.setMethod(method);
        usage.setStatusCode(statusCode);
        usage.setDurationMs(durationMs);
        usage.setIpAddress(ipAddress);
        usage.setUserAgent(userAgent);
        usage.setCreatedAt(Instant.now());

        apiKeyUsageRepository.save(usage);
    }

    /**
     * Get usage log for a specific API key.
     */
    public List<ApiKeyUsage> getUsageLog(String userId, String keyId, int limit) {
        // Verify ownership
        getKey(userId, keyId);
        return apiKeyUsageRepository.findByKeyIdAndCreatedAtAfter(
                keyId, Instant.now().minus(30, ChronoUnit.DAYS));
    }

    // --- Scheduled tasks ---

    /**
     * Expire keys that have passed their expiration date.
     * Runs every hour.
     */
    @Scheduled(fixedRate = 3600000)
    @Transactional
    public void expireOverdueKeys() {
        int count = apiKeyRepository.expireOverdueKeys(Instant.now());
        if (count > 0) {
            log.info("Expired {} overdue API keys", count);
        }
    }

    /**
     * Reset monthly quotas at the start of each month.
     * Runs every day at midnight.
     */
    @Scheduled(cron = "0 0 0 * * ?")
    @Transactional
    public void resetMonthlyQuotas() {
        Instant now = Instant.now();
        Instant nextReset = now.truncatedTo(ChronoUnit.DAYS)
                .plus(30 - now.atZone(java.time.ZoneId.systemDefault()).getDayOfMonth() + 1,
                        ChronoUnit.DAYS);
        int count = apiKeyRepository.resetMonthlyQuotas(now, nextReset);
        if (count > 0) {
            log.info("Reset monthly quotas for {} API keys", count);
        }
    }

    // --- Private helpers ---

    /**
     * Generate a raw API key: qk_ + 40 random URL-safe characters.
     */
    private String generateRawKey() {
        byte[] bytes = new byte[KEY_RANDOM_BYTES];
        SECURE_RANDOM.nextBytes(bytes);
        return "qk_" + Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    /**
     * SHA-256 hash of the raw key for storage.
     */
    private String sha256(String input) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(input.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }

    // --- DTO ---

    /**
     * Result of API key creation. Contains the raw key (shown only once).
     */
    public record ApiKeyCreationResult(
            String keyId,
            String keyName,
            String rawKey,
            String keyPrefix,
            String keyType,
            String scopes,
            Integer rateLimit,
            Integer quotaLimit,
            Instant expiresAt,
            Instant createdAt
    ) {}
}
