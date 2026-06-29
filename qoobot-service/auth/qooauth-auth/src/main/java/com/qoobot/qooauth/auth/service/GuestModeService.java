package com.qoobot.qooauth.auth.service;

import com.qoobot.qooauth.auth.service.TokenService.TokenPair;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.*;

/**
 * Guest Mode Service.
 * <p>
 * Provides limited, sandboxed access to QooBot devices for guests:
 * <ul>
 *   <li>Time-limited guest sessions</li>
 *   <li>Restricted feature set (no personal data access)</li>
 *   <li>Data isolation from owner's data</li>
 *   <li>Usage time limits</li>
 *   <li>Automatic cleanup on session expiry</li>
 * </ul>
 */
@Service
public class GuestModeService {

    private static final Logger log = LoggerFactory.getLogger(GuestModeService.class);

    private final RedisTemplate<String, String> redisTemplate;
    private final TokenService tokenService;
    private final SessionService sessionService;

    // Redis key prefixes
    private static final String GUEST_SESSION_KEY = "qooauth:guest:session:";
    private static final String GUEST_PROFILE_KEY = "qooauth:guest:profile:";

    // Default limits
    private static final Duration DEFAULT_SESSION_DURATION = Duration.ofHours(2);
    private static final Duration MAX_SESSION_DURATION = Duration.ofHours(24);

    // Restricted features for guests
    private static final Set<String> GUEST_ALLOWED_FEATURES = Set.of(
            "basic_movement",      // Basic robot movement
            "voice_commands",      // Voice command input
            "object_recognition",  // Basic object recognition
            "navigation_basic",    // Basic navigation
            "media_playback",      // Music/video playback
            "environment_sensors"  // Read environment sensor data
    );

    // Features explicitly blocked for guests
    private static final Set<String> GUEST_BLOCKED_FEATURES = Set.of(
            "personal_data",       // Access to owner's personal data
            "device_settings",     // Device configuration changes
            "purchase",           // In-app purchases
            "account_management",  // Account management
            "factory_reset",      // Factory reset
            "skill_installation", // Installing new skills
            "remote_access",      // Remote access configuration
            "data_export"         // Data export
    );

    public GuestModeService(RedisTemplate<String, String> redisTemplate,
                             TokenService tokenService,
                             SessionService sessionService) {
        this.redisTemplate = redisTemplate;
        this.tokenService = tokenService;
        this.sessionService = sessionService;
    }

    /**
     * Create a guest session on a device.
     *
     * @param deviceId       the device to create guest session on
     * @param guestName      display name for the guest
     * @param durationHours  session duration (max 24 hours)
     * @param allowedFeatures custom allowed features (null = default set)
     * @param ip             client IP
     * @param userAgent      client user agent
     * @return guest session info including access token
     */
    public GuestSession createGuestSession(String deviceId, String guestName,
                                            int durationHours, Set<String> allowedFeatures,
                                            String ip, String userAgent) {
        // Validate duration
        Duration duration = Duration.ofHours(Math.min(durationHours, MAX_SESSION_DURATION.toHours()));
        if (durationHours <= 0) {
            duration = DEFAULT_SESSION_DURATION;
        }

        String sessionId = UUID.randomUUID().toString();
        Instant now = Instant.now();
        Instant expiresAt = now.plus(duration);

        // Generate guest token
        TokenPair tokens = tokenService.issueTokens(
                "guest_" + sessionId,
                "guest@qoobot.local",
                guestName != null ? guestName : "Guest",
                null,
                "guest"
        );

        // Store guest session
        String sessionKey = GUEST_SESSION_KEY + sessionId;
        Map<String, String> sessionData = new HashMap<>();
        sessionData.put("session_id", sessionId);
        sessionData.put("device_id", deviceId);
        sessionData.put("guest_name", guestName != null ? guestName : "Guest");
        sessionData.put("created_at", now.toString());
        sessionData.put("expires_at", expiresAt.toString());
        sessionData.put("ip", ip);
        sessionData.put("user_agent", userAgent != null ? userAgent : "");

        Set<String> effectiveFeatures = allowedFeatures != null ? allowedFeatures : GUEST_ALLOWED_FEATURES;
        sessionData.put("allowed_features", String.join(",", effectiveFeatures));

        redisTemplate.opsForHash().putAll(sessionKey, sessionData);
        redisTemplate.expire(sessionKey, duration);

        log.info("Guest session created: device={}, guest={}, expires={}",
                deviceId, guestName, expiresAt);

        return new GuestSession(sessionId, deviceId, guestName,
                tokens.accessToken(), tokens.refreshToken(),
                now, expiresAt, effectiveFeatures);
    }

    /**
     * End a guest session.
     */
    public void endGuestSession(String sessionId) {
        String sessionKey = GUEST_SESSION_KEY + sessionId;
        redisTemplate.delete(sessionKey);

        // Revoke guest tokens
        sessionService.revokeAllSessions("guest_" + sessionId);

        log.info("Guest session ended: {}", sessionId);
    }

    /**
     * Get guest session info.
     */
    public GuestSession getGuestSession(String sessionId) {
        String sessionKey = GUEST_SESSION_KEY + sessionId;
        Map<Object, Object> entries = redisTemplate.opsForHash().entries(sessionKey);
        if (entries.isEmpty()) return null;

        String deviceId = String.valueOf(entries.getOrDefault("device_id", ""));
        String guestName = String.valueOf(entries.getOrDefault("guest_name", "Guest"));
        String createdAtStr = String.valueOf(entries.getOrDefault("created_at", ""));
        String expiresAtStr = String.valueOf(entries.getOrDefault("expires_at", ""));

        Instant createdAt = createdAtStr.isEmpty() || "null".equals(createdAtStr) ?
                Instant.now() : Instant.parse(createdAtStr);
        Instant expiresAt = expiresAtStr.isEmpty() || "null".equals(expiresAtStr) ?
                Instant.now() : Instant.parse(expiresAtStr);

        String featuresStr = String.valueOf(entries.getOrDefault("allowed_features", ""));
        Set<String> features = featuresStr.isEmpty() ?
                GUEST_ALLOWED_FEATURES : new HashSet<>(Arrays.asList(featuresStr.split(",")));

        return new GuestSession(sessionId, deviceId, guestName,
                null, null, createdAt, expiresAt, features);
    }

    /**
     * Check if a guest session is valid and not expired.
     */
    public boolean isValidSession(String sessionId) {
        GuestSession session = getGuestSession(sessionId);
        return session != null && !session.isExpired();
    }

    /**
     * Check if a feature is allowed for a guest session.
     */
    public boolean isFeatureAllowed(String sessionId, String feature) {
        GuestSession session = getGuestSession(sessionId);
        if (session == null || session.isExpired()) return false;
        return session.allowedFeatures.contains(feature);
    }

    /**
     * Extend a guest session.
     */
    public GuestSession extendSession(String sessionId, int additionalHours) {
        GuestSession session = getGuestSession(sessionId);
        if (session == null) {
            throw new IllegalArgumentException("Guest session not found: " + sessionId);
        }

        Instant newExpiresAt = session.expiresAt.plus(Duration.ofHours(additionalHours));
        Instant maxExpiresAt = session.createdAt.plus(MAX_SESSION_DURATION);
        if (newExpiresAt.isAfter(maxExpiresAt)) {
            newExpiresAt = maxExpiresAt;
        }

        String sessionKey = GUEST_SESSION_KEY + sessionId;
        redisTemplate.opsForHash().put(sessionKey, "expires_at", newExpiresAt.toString());
        redisTemplate.expire(sessionKey, Duration.between(Instant.now(), newExpiresAt));

        log.info("Guest session extended: {}, new expires: {}", sessionId, newExpiresAt);
        return new GuestSession(session.sessionId, session.deviceId, session.guestName,
                null, null, session.createdAt, newExpiresAt, session.allowedFeatures);
    }

    /**
     * List all active guest sessions on a device.
     */
    public List<GuestSession> listDeviceGuestSessions(String deviceId) {
        // In production, use Redis scan with pattern
        Set<String> keys = redisTemplate.keys(GUEST_SESSION_KEY + "*");
        if (keys == null) return Collections.emptyList();

        List<GuestSession> sessions = new ArrayList<>();
        for (String key : keys) {
            Map<Object, Object> entries = redisTemplate.opsForHash().entries(key);
            String devId = String.valueOf(entries.getOrDefault("device_id", ""));
            if (deviceId.equals(devId)) {
                String sessionId = key.substring(GUEST_SESSION_KEY.length());
                GuestSession session = getGuestSession(sessionId);
                if (session != null && !session.isExpired()) {
                    sessions.add(session);
                }
            }
        }
        return sessions;
    }

    /**
     * End all guest sessions on a device.
     */
    public void endAllDeviceGuestSessions(String deviceId) {
        List<GuestSession> sessions = listDeviceGuestSessions(deviceId);
        for (GuestSession s : sessions) {
            endGuestSession(s.sessionId);
        }
        log.info("All guest sessions ended for device: {}", deviceId);
    }

    /**
     * Clean up expired guest sessions.
     */
    public int cleanupExpiredSessions() {
        Set<String> keys = redisTemplate.keys(GUEST_SESSION_KEY + "*");
        if (keys == null) return 0;

        int cleaned = 0;
        for (String key : keys) {
            String expiresAtStr = String.valueOf(
                    redisTemplate.opsForHash().get(key, "expires_at"));
            if (expiresAtStr != null && !"null".equals(expiresAtStr)) {
                Instant expiresAt = Instant.parse(expiresAtStr);
                if (expiresAt.isBefore(Instant.now())) {
                    redisTemplate.delete(key);
                    cleaned++;
                }
            }
        }
        log.info("Cleaned up {} expired guest sessions", cleaned);
        return cleaned;
    }

    /**
     * Guest session data class.
     */
    public static class GuestSession {
        public final String sessionId;
        public final String deviceId;
        public final String guestName;
        public final String accessToken;
        public final String refreshToken;
        public final Instant createdAt;
        public final Instant expiresAt;
        public final Set<String> allowedFeatures;

        public GuestSession(String sessionId, String deviceId, String guestName,
                             String accessToken, String refreshToken,
                             Instant createdAt, Instant expiresAt,
                             Set<String> allowedFeatures) {
            this.sessionId = sessionId;
            this.deviceId = deviceId;
            this.guestName = guestName;
            this.accessToken = accessToken;
            this.refreshToken = refreshToken;
            this.createdAt = createdAt;
            this.expiresAt = expiresAt;
            this.allowedFeatures = allowedFeatures;
        }

        public boolean isExpired() {
            return Instant.now().isAfter(expiresAt);
        }

        public Duration remainingTime() {
            return Duration.between(Instant.now(), expiresAt);
        }
    }
}
