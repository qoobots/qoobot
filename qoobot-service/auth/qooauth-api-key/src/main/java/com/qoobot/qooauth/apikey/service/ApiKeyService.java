package com.qoobot.qooauth.apikey.service;

import com.qoobot.qooauth.apikey.dto.ApiKeyCreateRequest;
import com.qoobot.qooauth.apikey.dto.ApiKeyResponse;
import com.qoobot.qooauth.apikey.entity.ApiKey;
import com.qoobot.qooauth.apikey.repository.ApiKeyRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class ApiKeyService {

    private static final String API_KEY_PREFIX = "qoo_";
    private static final int KEY_BYTES = 32; // 256-bit
    private static final int PREFIX_LENGTH = 12;
    private static final int MAX_KEYS_PER_USER = 20;

    private final ApiKeyRepository apiKeyRepository;
    private final SecureRandom secureRandom = new SecureRandom();

    @Transactional
    public ApiKeyResponse generateApiKey(String userId, ApiKeyCreateRequest request) {
        // Check quota
        long activeKeys = apiKeyRepository.countByUserIdAndState(userId, "ACTIVE");
        if (activeKeys >= MAX_KEYS_PER_USER) {
            throw new IllegalStateException("Maximum active API keys (" + MAX_KEYS_PER_USER + ") reached for user: " + userId);
        }

        // Generate 256-bit random key
        byte[] keyBytes = new byte[KEY_BYTES];
        secureRandom.nextBytes(keyBytes);
        String rawKey = Base64.getUrlEncoder().withoutPadding().encodeToString(keyBytes);

        // Hash the key with SHA-256
        String keyHash = sha256(rawKey);

        // Extract prefix for lookups
        String keyPrefix = rawKey.substring(0, Math.min(PREFIX_LENGTH, rawKey.length()));

        // Ensure unique prefix
        while (apiKeyRepository.findByKeyPrefix(keyPrefix).isPresent()) {
            byte[] newKeyBytes = new byte[KEY_BYTES];
            secureRandom.nextBytes(newKeyBytes);
            rawKey = Base64.getUrlEncoder().withoutPadding().encodeToString(newKeyBytes);
            keyHash = sha256(rawKey);
            keyPrefix = rawKey.substring(0, Math.min(PREFIX_LENGTH, rawKey.length()));
        }

        ApiKey apiKey = ApiKey.builder()
            .keyId(UUID.randomUUID().toString().replace("-", ""))
            .userId(userId)
            .keyPrefix(keyPrefix)
            .keyHash(keyHash)
            .name(request.getName())
            .permissions(request.getPermissions())
            .state("ACTIVE")
            .expiresAt(request.getExpiresAt())
            .createdAt(Instant.now())
            .build();

        ApiKey saved = apiKeyRepository.save(apiKey);

        return ApiKeyResponse.builder()
            .keyId(saved.getKeyId())
            .name(saved.getName())
            .apiKey(API_KEY_PREFIX + rawKey)
            .permissions(saved.getPermissions())
            .state(saved.getState())
            .createdAt(saved.getCreatedAt())
            .expiresAt(saved.getExpiresAt())
            .build();
    }

    @Transactional
    public ApiKeyResponse rotateKey(String keyId, String userId) {
        ApiKey existing = apiKeyRepository.findById(keyId)
            .orElseThrow(() -> new IllegalArgumentException("API key not found: " + keyId));

        if (!existing.getUserId().equals(userId)) {
            throw new SecurityException("API key does not belong to user: " + userId);
        }

        // Generate new key material
        byte[] keyBytes = new byte[KEY_BYTES];
        secureRandom.nextBytes(keyBytes);
        String rawKey = Base64.getUrlEncoder().withoutPadding().encodeToString(keyBytes);
        String keyHash = sha256(rawKey);
        String keyPrefix = rawKey.substring(0, Math.min(PREFIX_LENGTH, rawKey.length()));

        existing.setKeyPrefix(keyPrefix);
        existing.setKeyHash(keyHash);

        ApiKey saved = apiKeyRepository.save(existing);

        return ApiKeyResponse.builder()
            .keyId(saved.getKeyId())
            .name(saved.getName())
            .apiKey(API_KEY_PREFIX + rawKey)
            .permissions(saved.getPermissions())
            .state(saved.getState())
            .createdAt(saved.getCreatedAt())
            .expiresAt(saved.getExpiresAt())
            .lastUsedAt(saved.getLastUsedAt())
            .build();
    }

    @Transactional
    public void revokeKey(String keyId, String userId) {
        ApiKey existing = apiKeyRepository.findById(keyId)
            .orElseThrow(() -> new IllegalArgumentException("API key not found: " + keyId));

        if (!existing.getUserId().equals(userId)) {
            throw new SecurityException("API key does not belong to user: " + userId);
        }

        existing.setState("REVOKED");
        existing.setRevokedAt(Instant.now());
        apiKeyRepository.save(existing);

        log.info("API key {} revoked for user {}", keyId, userId);
    }

    public Optional<ApiKey> validateApiKey(String rawApiKey) {
        // Strip prefix if present
        String keyMaterial = rawApiKey.startsWith(API_KEY_PREFIX)
            ? rawApiKey.substring(API_KEY_PREFIX.length())
            : rawApiKey;

        if (keyMaterial.length() < PREFIX_LENGTH) {
            return Optional.empty();
        }

        String keyPrefix = keyMaterial.substring(0, PREFIX_LENGTH);
        return apiKeyRepository.findByKeyPrefix(keyPrefix)
            .filter(k -> "ACTIVE".equals(k.getState()))
            .filter(k -> {
                // Check expiration
                if (k.getExpiresAt() != null && k.getExpiresAt().isBefore(Instant.now())) {
                    return false;
                }
                // Hash comparison
                return sha256(keyMaterial).equals(k.getKeyHash());
            })
            .map(k -> {
                // Update last used timestamp
                k.setLastUsedAt(Instant.now());
                apiKeyRepository.save(k);
                return k;
            });
    }

    @Transactional(readOnly = true)
    public List<ApiKeyResponse> listByUser(String userId) {
        return apiKeyRepository.findByUserId(userId).stream()
            .map(k -> ApiKeyResponse.builder()
                .keyId(k.getKeyId())
                .name(k.getName())
                .apiKey(null) // Never return raw key on list
                .permissions(k.getPermissions())
                .state(k.getState())
                .createdAt(k.getCreatedAt())
                .expiresAt(k.getExpiresAt())
                .lastUsedAt(k.getLastUsedAt())
                .build())
            .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public long checkQuota(String userId) {
        long activeKeys = apiKeyRepository.countByUserIdAndState(userId, "ACTIVE");
        return Math.max(0, MAX_KEYS_PER_USER - activeKeys);
    }

    private String sha256(String input) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(input.getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 algorithm not available", e);
        }
    }
}
