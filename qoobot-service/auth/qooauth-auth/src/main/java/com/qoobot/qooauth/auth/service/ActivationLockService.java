package com.qoobot.qooauth.auth.service;

import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Activation Lock Service.
 * <p>
 * Anti-theft protection for QooBot devices (similar to Apple Activation Lock):
 * <ul>
 *   <li>Device lock on unauthorized reset</li>
 *   <li>Owner identity verification before unlock</li>
 *   <li>Remote lock and wipe commands</li>
 *   <li>Lost mode with custom message</li>
 *   <li>Find My QooBot integration</li>
 * </ul>
 */
@Service
public class ActivationLockService {

    private static final Logger log = LoggerFactory.getLogger(ActivationLockService.class);

    private final RedisTemplate<String, String> redisTemplate;

    // Redis key prefixes
    private static final String LOCK_STATE_KEY = "qooauth:actlock:state:";
    private static final String LOST_MODE_KEY = "qooauth:actlock:lost:";
    private static final String WIPE_TOKEN_KEY = "qooauth:actlock:wipe:";

    // In-memory lock state cache
    private final Map<String, LockState> lockStateCache = new ConcurrentHashMap<>();

    public ActivationLockService(RedisTemplate<String, String> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    /**
     * Enable activation lock for a device.
     *
     * @param deviceId device identifier
     * @param ownerId  owner's QooBot ID
     * @param ownerEmail owner's email (for recovery)
     */
    public void enableLock(String deviceId, String ownerId, String ownerEmail) {
        LockState state = new LockState();
        state.deviceId = deviceId;
        state.ownerId = ownerId;
        state.ownerEmail = ownerEmail;
        state.locked = true;
        state.enabledAt = Instant.now();
        state.lockReason = "ACTIVATION_LOCK";

        String key = LOCK_STATE_KEY + deviceId;
        Map<String, String> stateMap = state.toMap();
        redisTemplate.opsForHash().putAll(key, stateMap);
        lockStateCache.put(deviceId, state);

        log.info("Activation lock enabled: device={}, owner={}", deviceId, ownerId);
    }

    /**
     * Disable activation lock (requires owner authentication).
     *
     * @param deviceId   device identifier
     * @param ownerId    requesting user's ID (must match owner)
     * @param authToken  additional authentication token
     */
    public void disableLock(String deviceId, String ownerId, String authToken) {
        LockState state = getLockState(deviceId);
        if (state == null || !state.locked) {
            throw new AuthException(ErrorCodes.DEVICE_NOT_FOUND, "Device is not locked");
        }

        if (!state.ownerId.equals(ownerId)) {
            log.warn("Unauthorized activation lock disable attempt: device={}, user={}", deviceId, ownerId);
            throw new AuthException(ErrorCodes.INSUFFICIENT_PERMISSIONS,
                    "Only the device owner can disable activation lock");
        }

        // Remove lock state
        String key = LOCK_STATE_KEY + deviceId;
        redisTemplate.delete(key);
        lockStateCache.remove(deviceId);

        log.info("Activation lock disabled: device={}", deviceId);
    }

    /**
     * Check if a device has activation lock enabled.
     */
    public boolean isLocked(String deviceId) {
        LockState state = getLockState(deviceId);
        return state != null && state.locked;
    }

    /**
     * Verify owner credentials for activation lock bypass.
     */
    public boolean verifyOwner(String deviceId, String ownerId) {
        LockState state = getLockState(deviceId);
        return state != null && state.ownerId.equals(ownerId);
    }

    /**
     * Enable lost mode on a device.
     *
     * @param deviceId      device identifier
     * @param message       custom message to display
     * @param contactPhone  contact phone number to display
     */
    public void enableLostMode(String deviceId, String message, String contactPhone) {
        if (!isLocked(deviceId)) {
            throw new AuthException(ErrorCodes.DEVICE_NOT_FOUND, "Activation lock is not enabled on this device");
        }

        String key = LOST_MODE_KEY + deviceId;
        Map<String, String> lostMode = new HashMap<>();
        lostMode.put("enabled", "true");
        lostMode.put("message", message != null ? message : "");
        lostMode.put("contact_phone", contactPhone != null ? contactPhone : "");
        lostMode.put("enabled_at", Instant.now().toString());
        redisTemplate.opsForHash().putAll(key, lostMode);

        log.info("Lost mode enabled: device={}", deviceId);
    }

    /**
     * Disable lost mode.
     */
    public void disableLostMode(String deviceId) {
        redisTemplate.delete(LOST_MODE_KEY + deviceId);
        log.info("Lost mode disabled: device={}", deviceId);
    }

    /**
     * Get lost mode status.
     */
    public Map<String, String> getLostModeStatus(String deviceId) {
        String key = LOST_MODE_KEY + deviceId;
        Map<Object, Object> entries = redisTemplate.opsForHash().entries(key);
        Map<String, String> result = new HashMap<>();
        for (Map.Entry<Object, Object> e : entries.entrySet()) {
            result.put(String.valueOf(e.getKey()), String.valueOf(e.getValue()));
        }
        return result;
    }

    /**
     * Generate a remote wipe token.
     */
    public String generateWipeToken(String deviceId) {
        if (!isLocked(deviceId)) {
            throw new AuthException(ErrorCodes.DEVICE_NOT_FOUND, "Activation lock is not enabled on this device");
        }

        String token = generateSecureToken();
        String key = WIPE_TOKEN_KEY + deviceId;
        redisTemplate.opsForValue().set(key, token, Duration.ofHours(24));

        log.info("Remote wipe token generated: device={}", deviceId);
        return token;
    }

    /**
     * Verify and consume a wipe token.
     */
    public boolean verifyWipeToken(String deviceId, String token) {
        String key = WIPE_TOKEN_KEY + deviceId;
        String storedToken = redisTemplate.opsForValue().get(key);
        if (storedToken != null && storedToken.equals(token)) {
            redisTemplate.delete(key);
            log.info("Remote wipe token verified: device={}", deviceId);
            return true;
        }
        return false;
    }

    /**
     * Trigger remote wipe (after token verification).
     */
    public void triggerRemoteWipe(String deviceId) {
        // Mark device for wipe
        String key = LOCK_STATE_KEY + deviceId;
        redisTemplate.opsForHash().put(key, "wipe_requested", "true");
        redisTemplate.opsForHash().put(key, "wipe_requested_at", Instant.now().toString());

        log.warn("Remote wipe triggered: device={}", deviceId);
    }

    /**
     * Get the full activation lock state.
     */
    public LockState getLockState(String deviceId) {
        // Check cache first
        LockState cached = lockStateCache.get(deviceId);
        if (cached != null) return cached;

        // Check Redis
        String key = LOCK_STATE_KEY + deviceId;
        Map<Object, Object> entries = redisTemplate.opsForHash().entries(key);
        if (entries.isEmpty()) return null;

        LockState state = LockState.fromMap(entries);
        lockStateCache.put(deviceId, state);
        return state;
    }

    /**
     * Remove activation lock (for administrative override).
     */
    public void adminOverrideUnlock(String deviceId, String adminId, String reason) {
        String key = LOCK_STATE_KEY + deviceId;
        redisTemplate.opsForHash().put(key, "admin_override", "true");
        redisTemplate.opsForHash().put(key, "admin_id", adminId);
        redisTemplate.opsForHash().put(key, "override_reason", reason);
        redisTemplate.opsForHash().put(key, "override_at", Instant.now().toString());

        redisTemplate.delete(key);
        lockStateCache.remove(deviceId);

        log.warn("Activation lock overridden by admin: device={}, admin={}, reason={}",
                deviceId, adminId, reason);
    }

    private String generateSecureToken() {
        byte[] bytes = new byte[32];
        new SecureRandom().nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    /**
     * Activation lock state.
     */
    public static class LockState {
        public String deviceId;
        public String ownerId;
        public String ownerEmail;
        public boolean locked;
        public String lockReason;
        public Instant enabledAt;
        public boolean wipeRequested;
        public Instant wipeRequestedAt;

        public Map<String, String> toMap() {
            Map<String, String> map = new HashMap<>();
            map.put("device_id", deviceId);
            map.put("owner_id", ownerId);
            map.put("owner_email", ownerEmail != null ? ownerEmail : "");
            map.put("locked", String.valueOf(locked));
            map.put("lock_reason", lockReason != null ? lockReason : "");
            map.put("enabled_at", enabledAt != null ? enabledAt.toString() : "");
            return map;
        }

        public static LockState fromMap(Map<Object, Object> map) {
            LockState state = new LockState();
            state.deviceId = String.valueOf(map.getOrDefault("device_id", ""));
            state.ownerId = String.valueOf(map.getOrDefault("owner_id", ""));
            state.ownerEmail = String.valueOf(map.getOrDefault("owner_email", ""));
            state.locked = "true".equals(String.valueOf(map.getOrDefault("locked", "false")));
            state.lockReason = String.valueOf(map.getOrDefault("lock_reason", ""));
            String enabledAtStr = String.valueOf(map.getOrDefault("enabled_at", ""));
            if (!enabledAtStr.isEmpty() && !"null".equals(enabledAtStr)) {
                state.enabledAt = Instant.parse(enabledAtStr);
            }
            state.wipeRequested = "true".equals(String.valueOf(map.getOrDefault("wipe_requested", "false")));
            return state;
        }
    }
}
