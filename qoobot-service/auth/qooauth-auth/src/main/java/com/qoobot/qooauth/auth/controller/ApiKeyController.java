package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.entity.ApiKey;
import com.qoobot.qooauth.auth.entity.ApiKeyUsage;
import com.qoobot.qooauth.auth.service.ApiKeyService;
import com.qoobot.qooauth.auth.service.ApiKeyService.ApiKeyCreationResult;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.security.Principal;
import java.util.List;
import java.util.Map;

/**
 * API Key management REST controller.
 *
 * Endpoints:
 *   POST   /api/v1/auth/api-keys             — Create a new API key
 *   GET    /api/v1/auth/api-keys             — List all API keys for current user
 *   GET    /api/v1/auth/api-keys/{keyId}     — Get a specific API key
 *   POST   /api/v1/auth/api-keys/{keyId}/rotate   — Rotate (replace) an API key
 *   DELETE /api/v1/auth/api-keys/{keyId}     — Revoke an API key
 *   GET    /api/v1/auth/api-keys/{keyId}/usage    — Get usage log for a key
 *   POST   /api/v1/auth/api-keys/validate    — Validate an API key (internal/API gateway use)
 */
@RestController
@RequestMapping("/api/v1/auth/api-keys")
public class ApiKeyController {

    private final ApiKeyService apiKeyService;

    public ApiKeyController(ApiKeyService apiKeyService) {
        this.apiKeyService = apiKeyService;
    }

    /**
     * Create a new API key.
     * The raw key is returned in the response — it will NOT be shown again.
     */
    @PostMapping
    public ResponseEntity<Map<String, Object>> createKey(
            Principal principal,
            @RequestBody CreateKeyRequest request) {
        ApiKeyCreationResult result = apiKeyService.createKey(
                principal.getName(),
                request.keyName(),
                request.keyType(),
                request.scopes(),
                request.resourceIds(),
                request.rateLimit(),
                request.quotaLimit(),
                request.expiresInDays()
        );

        return ResponseEntity.status(HttpStatus.CREATED).body(Map.of(
                "key_id", result.keyId(),
                "key_name", result.keyName(),
                "api_key", result.rawKey(),
                "key_prefix", result.keyPrefix(),
                "key_type", result.keyType(),
                "scopes", result.scopes(),
                "rate_limit", result.rateLimit(),
                "quota_limit", result.quotaLimit(),
                "expires_at", result.expiresAt() != null ? result.expiresAt().toString() : null,
                "created_at", result.createdAt().toString(),
                "warning", "Store this key securely. It will not be shown again."
        ));
    }

    /**
     * List all API keys for the authenticated user.
     * Raw keys are never returned — only metadata.
     */
    @GetMapping
    public ResponseEntity<List<Map<String, Object>>> listKeys(Principal principal) {
        List<ApiKey> keys = apiKeyService.listKeys(principal.getName());

        List<Map<String, Object>> response = keys.stream()
                .map(this::toKeyMetadata)
                .toList();

        return ResponseEntity.ok(response);
    }

    /**
     * Get a specific API key's metadata.
     */
    @GetMapping("/{keyId}")
    public ResponseEntity<Map<String, Object>> getKey(
            Principal principal,
            @PathVariable String keyId) {
        ApiKey key = apiKeyService.getKey(principal.getName(), keyId);
        return ResponseEntity.ok(toKeyMetadata(key));
    }

    /**
     * Rotate an API key: revoke old, create new.
     * Returns the new raw key.
     */
    @PostMapping("/{keyId}/rotate")
    public ResponseEntity<Map<String, Object>> rotateKey(
            Principal principal,
            @PathVariable String keyId) {
        ApiKeyCreationResult result = apiKeyService.rotateKey(principal.getName(), keyId);

        return ResponseEntity.ok(Map.of(
                "key_id", result.keyId(),
                "key_name", result.keyName(),
                "api_key", result.rawKey(),
                "key_prefix", result.keyPrefix(),
                "key_type", result.keyType(),
                "scopes", result.scopes(),
                "rate_limit", result.rateLimit(),
                "quota_limit", result.quotaLimit(),
                "expires_at", result.expiresAt() != null ? result.expiresAt().toString() : null,
                "created_at", result.createdAt().toString(),
                "warning", "Store this key securely. It will not be shown again."
        ));
    }

    /**
     * Revoke an API key.
     */
    @DeleteMapping("/{keyId}")
    public ResponseEntity<Map<String, String>> revokeKey(
            Principal principal,
            @PathVariable String keyId,
            @RequestBody(required = false) RevokeKeyRequest request) {
        String reason = request != null ? request.reason() : "User requested";
        apiKeyService.revokeKey(principal.getName(), keyId, reason);
        return ResponseEntity.ok(Map.of(
                "key_id", keyId,
                "state", "REVOKED",
                "message", "API key has been revoked"
        ));
    }

    /**
     * Get usage log for a specific API key (last 30 days).
     */
    @GetMapping("/{keyId}/usage")
    public ResponseEntity<List<Map<String, Object>>> getUsage(
            Principal principal,
            @PathVariable String keyId,
            @RequestParam(defaultValue = "100") int limit) {
        List<ApiKeyUsage> usages = apiKeyService.getUsageLog(
                principal.getName(), keyId, limit);

        List<Map<String, Object>> response = usages.stream()
                .map(u -> {
                    Map<String, Object> entry = new java.util.LinkedHashMap<>();
                    entry.put("usage_id", u.getUsageId());
                    entry.put("endpoint", u.getEndpoint());
                    entry.put("method", u.getMethod());
                    entry.put("status_code", u.getStatusCode());
                    entry.put("duration_ms", u.getDurationMs());
                    entry.put("ip_address", u.getIpAddress());
                    entry.put("created_at", u.getCreatedAt().toString());
                    return entry;
                })
                .toList();

        return ResponseEntity.ok(response);
    }

    /**
     * Validate an API key (called by API gateway / resource servers).
     * Public endpoint — does not require JWT authentication.
     */
    @PostMapping("/validate")
    public ResponseEntity<Map<String, Object>> validateKey(
            @RequestBody ValidateKeyRequest request) {
        ApiKey key = apiKeyService.validateKey(request.apiKey());

        return ResponseEntity.ok(Map.of(
                "valid", true,
                "key_id", key.getKeyId(),
                "user_id", key.getUserId(),
                "key_type", key.getKeyType(),
                "scopes", key.getScopes(),
                "resource_ids", key.getResourceIds(),
                "rate_limit", key.getRateLimit(),
                "quota_remaining", key.getQuotaLimit() - key.getQuotaUsed()
        ));
    }

    // --- Private helpers ---

    private Map<String, Object> toKeyMetadata(ApiKey key) {
        Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("key_id", key.getKeyId());
        map.put("key_name", key.getKeyName());
        map.put("key_prefix", key.getKeyPrefix());
        map.put("key_type", key.getKeyType());
        map.put("state", key.getState());
        map.put("scopes", key.getScopes());
        map.put("resource_ids", key.getResourceIds());
        map.put("rate_limit", key.getRateLimit());
        map.put("quota_limit", key.getQuotaLimit());
        map.put("quota_used", key.getQuotaUsed());
        map.put("quota_reset_at", key.getQuotaResetAt() != null ? key.getQuotaResetAt().toString() : null);
        map.put("last_used_at", key.getLastUsedAt() != null ? key.getLastUsedAt().toString() : null);
        map.put("expires_at", key.getExpiresAt() != null ? key.getExpiresAt().toString() : null);
        map.put("created_at", key.getCreatedAt().toString());
        return map;
    }

    // --- Request DTOs ---

    public record CreateKeyRequest(
            String keyName,
            String keyType,
            String scopes,
            String resourceIds,
            Integer rateLimit,
            Integer quotaLimit,
            Integer expiresInDays
    ) {}

    public record RevokeKeyRequest(
            String reason
    ) {}

    public record ValidateKeyRequest(
            String apiKey
    ) {}
}
