package com.qoobot.qooauth.developer.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Developer sandbox service providing resource-isolated development environments.
 * Each sandbox has a TTL-based expiration with automatic data cleanup.
 */
@Slf4j
@Service
public class SandboxService {

    private static final long DEFAULT_TTL_SECONDS = 3600L; // 1 hour
    private static final long MAX_TTL_SECONDS = 86400L; // 24 hours
    private static final int MAX_SANDBOXES_PER_USER = 3;

    private final Map<String, Sandbox> sandboxes = new ConcurrentHashMap<>();

    /**
     * Create a new sandbox for a developer.
     */
    public Sandbox createSandbox(String userId, long ttlSeconds) {
        // Clean up expired sandboxes for this user first
        cleanupExpiredForUser(userId);

        // Check quota
        long activeCount = sandboxes.values().stream()
            .filter(s -> s.userId.equals(userId) && !s.isExpired())
            .count();

        if (activeCount >= MAX_SANDBOXES_PER_USER) {
            throw new IllegalStateException(
                "Maximum active sandboxes (" + MAX_SANDBOXES_PER_USER + ") reached for user: " + userId);
        }

        long effectiveTtl = Math.min(Math.max(ttlSeconds, 60L), MAX_TTL_SECONDS);

        Sandbox sandbox = new Sandbox(
            UUID.randomUUID().toString().replace("-", ""),
            userId,
            Instant.now(),
            Instant.now().plusSeconds(effectiveTtl),
            effectiveTtl
        );

        sandboxes.put(sandbox.id, sandbox);
        log.info("Sandbox {} created for user {} (TTL: {}s)", sandbox.id, userId, effectiveTtl);
        return sandbox;
    }

    /**
     * Get the status of a developer's sandboxes.
     */
    public SandboxStatus getSandboxStatus(String userId) {
        cleanupExpiredForUser(userId);

        var userSandboxes = sandboxes.values().stream()
            .filter(s -> s.userId.equals(userId) && !s.isExpired())
            .toList();

        return new SandboxStatus(
            userId,
            userSandboxes.size(),
            MAX_SANDBOXES_PER_USER,
            userSandboxes.stream().map(Sandbox::toDto).toList()
        );
    }

    /**
     * Destroy a specific sandbox and clean up its data.
     */
    public void destroySandbox(String sandboxId, String userId) {
        Sandbox sandbox = sandboxes.get(sandboxId);
        if (sandbox == null) {
            throw new IllegalArgumentException("Sandbox not found: " + sandboxId);
        }
        if (!sandbox.userId.equals(userId)) {
            throw new SecurityException("Sandbox does not belong to user: " + userId);
        }

        sandboxes.remove(sandboxId);
        log.info("Sandbox {} destroyed for user {}", sandboxId, userId);
    }

    /**
     * Extend the TTL of a sandbox.
     */
    public Sandbox extendSandbox(String sandboxId, String userId, long additionalSeconds) {
        Sandbox sandbox = sandboxes.get(sandboxId);
        if (sandbox == null || sandbox.isExpired()) {
            throw new IllegalArgumentException("Sandbox not found or expired: " + sandboxId);
        }
        if (!sandbox.userId.equals(userId)) {
            throw new SecurityException("Sandbox does not belong to user: " + userId);
        }

        long newTtl = Math.min(sandbox.ttlSeconds + additionalSeconds, MAX_TTL_SECONDS);
        Sandbox updated = new Sandbox(
            sandbox.id, sandbox.userId, sandbox.createdAt,
            sandbox.createdAt.plusSeconds(newTtl), newTtl
        );
        sandboxes.put(sandboxId, updated);
        log.info("Sandbox {} TTL extended by {}s for user {}", sandboxId, additionalSeconds, userId);
        return updated;
    }

    private void cleanupExpiredForUser(String userId) {
        sandboxes.entrySet().removeIf(entry ->
            entry.getValue().userId.equals(userId) && entry.getValue().isExpired()
        );
    }

    // ---- Inner classes ----

    public static class Sandbox {
        public final String id;
        public final String userId;
        public final Instant createdAt;
        public final Instant expiresAt;
        public final long ttlSeconds;

        Sandbox(String id, String userId, Instant createdAt, Instant expiresAt, long ttlSeconds) {
            this.id = id;
            this.userId = userId;
            this.createdAt = createdAt;
            this.expiresAt = expiresAt;
            this.ttlSeconds = ttlSeconds;
        }

        public boolean isExpired() {
            return Instant.now().isAfter(expiresAt);
        }

        public Map<String, Object> toDto() {
            return Map.of(
                "id", id,
                "created_at", createdAt.toString(),
                "expires_at", expiresAt.toString(),
                "ttl_seconds", ttlSeconds,
                "expired", isExpired()
            );
        }
    }

    public record SandboxStatus(String userId, int activeCount, int maxAllowed, java.util.List<Map<String, Object>> sandboxes) {}
}
