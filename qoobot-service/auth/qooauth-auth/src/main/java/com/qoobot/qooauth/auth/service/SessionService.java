package com.qoobot.qooauth.auth.service;

import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Set;
import java.util.UUID;

/**
 * Session management service backed by Redis.
 * Manages user sessions with concurrent session control.
 */
@Service
public class SessionService {

    private static final Duration SESSION_TTL = Duration.ofHours(1);
    private static final int MAX_CONCURRENT_SESSIONS = 5;

    private final RedisTemplate<String, String> redisTemplate;

    public SessionService(RedisTemplate<String, String> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    /**
     * Create a new session for a user.
     */
    public String createSession(String userId, String deviceId, String clientId,
                                 String ip, String userAgent) {
        // Check concurrent session limit
        String sessionsKey = "qooauth:user_sessions:" + userId;
        Long sessionCount = redisTemplate.opsForSet().size(sessionsKey);
        if (sessionCount != null && sessionCount >= MAX_CONCURRENT_SESSIONS) {
            // Remove oldest session
            String oldestSession = redisTemplate.opsForSet().pop(sessionsKey);
            if (oldestSession != null) {
                redisTemplate.delete("qooauth:session:" + oldestSession);
            }
        }

        String sessionId = UUID.randomUUID().toString();
        String sessionKey = "qooauth:session:" + sessionId;

        redisTemplate.opsForHash().put(sessionKey, "user_id", userId);
        redisTemplate.opsForHash().put(sessionKey, "device_id", deviceId != null ? deviceId : "");
        redisTemplate.opsForHash().put(sessionKey, "client_id", clientId != null ? clientId : "");
        redisTemplate.opsForHash().put(sessionKey, "ip", ip != null ? ip : "");
        redisTemplate.opsForHash().put(sessionKey, "user_agent", userAgent != null ? userAgent : "");
        redisTemplate.opsForHash().put(sessionKey, "created_at", String.valueOf(System.currentTimeMillis()));

        redisTemplate.expire(sessionKey, SESSION_TTL);
        redisTemplate.opsForSet().add(sessionsKey, sessionId);
        redisTemplate.expire(sessionsKey, SESSION_TTL);

        return sessionId;
    }

    /**
     * Get active sessions for a user.
     */
    public Set<String> getUserSessions(String userId) {
        return redisTemplate.opsForSet().members("qooauth:user_sessions:" + userId);
    }

    /**
     * Revoke a specific session.
     */
    public void revokeSession(String userId, String sessionId) {
        redisTemplate.delete("qooauth:session:" + sessionId);
        redisTemplate.opsForSet().remove("qooauth:user_sessions:" + userId, sessionId);
    }

    /**
     * Revoke all sessions for a user (remote logout).
     */
    public void revokeAllSessions(String userId) {
        String sessionsKey = "qooauth:user_sessions:" + userId;
        Set<String> sessions = redisTemplate.opsForSet().members(sessionsKey);
        if (sessions != null) {
            for (String sessionId : sessions) {
                redisTemplate.delete("qooauth:session:" + sessionId);
            }
        }
        redisTemplate.delete(sessionsKey);
    }

    /**
     * Check if a session exists and refresh its TTL.
     */
    public boolean touchSession(String sessionId) {
        String sessionKey = "qooauth:session:" + sessionId;
        Boolean exists = redisTemplate.hasKey(sessionKey);
        if (Boolean.TRUE.equals(exists)) {
            redisTemplate.expire(sessionKey, SESSION_TTL);
            return true;
        }
        return false;
    }
}
