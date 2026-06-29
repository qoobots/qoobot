 package com.qoobot.qooauth.auth.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.connection.Message;
import org.springframework.data.redis.connection.MessageListener;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.listener.ChannelTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;

/**
 * SSO (Single Sign-On) session management service.
 *
 * Responsibilities:
 * 1. Global SSO session lifecycle — create, refresh, terminate
 * 2. Token-to-session binding — all tokens carry sid claim for cross-service validation
 * 3. Logout propagation — Redis Pub/Sub to notify all services of session termination
 * 4. Session introspection — check if a session is still valid from any service
 */
@Service
public class SsoSessionService {

    private static final Logger log = LoggerFactory.getLogger(SsoSessionService.class);

    private static final String SSO_SESSION_PREFIX = "qooauth:sso_session:";
    private static final String SSO_USER_SESSIONS_PREFIX = "qooauth:sso_user_sessions:";
    private static final String SSO_LOGOUT_CHANNEL = "qooauth:sso:logout";

    // SSO session TTL: 8 hours (renewable on activity)
    private static final Duration SSO_SESSION_TTL = Duration.ofHours(8);
    // Maximum SSO sessions per user
    private static final int MAX_SSO_SESSIONS = 10;

    private final RedisTemplate<String, String> redisTemplate;
    private final StringRedisTemplate stringRedisTemplate;
    private final RedisMessageListenerContainer listenerContainer;
    private final ObjectMapper objectMapper;

    // Local listeners for logout events (in-process handlers)
    private final Map<String, Consumer<SsoSession>> logoutListeners = new ConcurrentHashMap<>();

    public SsoSessionService(RedisTemplate<String, String> redisTemplate,
                              StringRedisTemplate stringRedisTemplate,
                              RedisMessageListenerContainer listenerContainer,
                              ObjectMapper objectMapper) {
        this.redisTemplate = redisTemplate;
        this.stringRedisTemplate = stringRedisTemplate;
        this.listenerContainer = listenerContainer;
        this.objectMapper = objectMapper;
    }

    @PostConstruct
    private void init() {
        // Subscribe to logout channel via Spring's RedisMessageListenerContainer
        listenerContainer.addMessageListener(new SsoLogoutMessageListener(),
                new ChannelTopic(SSO_LOGOUT_CHANNEL));
        log.info("SSO logout listener registered on channel: {}", SSO_LOGOUT_CHANNEL);
    }

    // ========================================================================
    // SSO Session Lifecycle
    // ========================================================================

    /**
     * Create a new global SSO session after successful authentication.
     *
     * @param userId    authenticated user ID
     * @param email     user email
     * @param clientId  originating client/service ID
     * @param ip        client IP address
     * @param userAgent client User-Agent
     * @return the SSO session ID (sid)
     */
    public SsoSession createSession(String userId, String email, String clientId,
                                     String ip, String userAgent) {
        String sessionId = UUID.randomUUID().toString();
        Instant now = Instant.now();

        SsoSession session = new SsoSession(
                sessionId, userId, email, clientId, ip, userAgent,
                now, now, SSO_SESSION_TTL.toSeconds()
        );

        // Enforce max sessions per user
        String userSessionsKey = SSO_USER_SESSIONS_PREFIX + userId;
        Long count = redisTemplate.opsForSet().size(userSessionsKey);
        if (count != null && count >= MAX_SSO_SESSIONS) {
            // Remove oldest session
            String oldest = redisTemplate.opsForSet().pop(userSessionsKey);
            if (oldest != null) {
                redisTemplate.delete(SSO_SESSION_PREFIX + oldest);
            }
        }

        // Store session
        String sessionKey = SSO_SESSION_PREFIX + sessionId;
        redisTemplate.opsForValue().set(sessionKey, toJson(session), SSO_SESSION_TTL);

        // Track in user's session set
        redisTemplate.opsForSet().add(userSessionsKey, sessionId);
        redisTemplate.expire(userSessionsKey, SSO_SESSION_TTL);

        log.info("SSO session created: sid={}, user={}, client={}", sessionId, userId, clientId);
        return session;
    }

    /**
     * Refresh an SSO session (extend TTL, update last activity).
     */
    public boolean refreshSession(String sessionId) {
        String sessionKey = SSO_SESSION_PREFIX + sessionId;
        String json = redisTemplate.opsForValue().get(sessionKey);
        if (json == null) {
            return false;
        }

        try {
            SsoSession session = fromJson(json);
            session = new SsoSession(
                    session.sessionId, session.userId, session.email,
                    session.clientId, session.ipAddress, session.userAgent,
                    session.createdAt, Instant.now(), SSO_SESSION_TTL.toSeconds()
            );
            redisTemplate.opsForValue().set(sessionKey, toJson(session), SSO_SESSION_TTL);

            // Also refresh user-sessions set
            String userSessionsKey = SSO_USER_SESSIONS_PREFIX + session.userId;
            redisTemplate.expire(userSessionsKey, SSO_SESSION_TTL);

            return true;
        } catch (Exception e) {
            log.warn("Failed to refresh SSO session {}", sessionId, e);
            return false;
        }
    }

    /**
     * Validate that an SSO session exists and is active.
     * Called by resource servers via introspection or direct Redis access.
     */
    public boolean isValidSession(String sessionId) {
        if (sessionId == null) return false;
        return Boolean.TRUE.equals(redisTemplate.hasKey(SSO_SESSION_PREFIX + sessionId));
    }

    /**
     * Get SSO session details.
     */
    public SsoSession getSession(String sessionId) {
        String json = redisTemplate.opsForValue().get(SSO_SESSION_PREFIX + sessionId);
        if (json == null) return null;
        try {
            return fromJson(json);
        } catch (JsonProcessingException e) {
            log.warn("Failed to parse SSO session {}", sessionId, e);
            return null;
        }
    }

    /**
     * Get all active SSO sessions for a user.
     */
    public List<SsoSession> getUserSessions(String userId) {
        String userSessionsKey = SSO_USER_SESSIONS_PREFIX + userId;
        Set<String> sessionIds = redisTemplate.opsForSet().members(userSessionsKey);
        if (sessionIds == null || sessionIds.isEmpty()) return Collections.emptyList();

        List<SsoSession> sessions = new ArrayList<>();
        for (String sid : sessionIds) {
            SsoSession session = getSession(sid);
            if (session != null) {
                sessions.add(session);
            } else {
                // Clean up stale reference
                redisTemplate.opsForSet().remove(userSessionsKey, sid);
            }
        }
        sessions.sort((a, b) -> b.lastActivityAt.compareTo(a.lastActivityAt));
        return sessions;
    }

    // ========================================================================
    // Logout Propagation
    // ========================================================================

    /**
     * Terminate a specific SSO session and propagate logout event.
     * This is the primary logout mechanism:
     * 1. Remove session from Redis
     * 2. Publish logout event to Redis Pub/Sub
     * 3. All listening services (gateway, qoocloud, etc.) invalidate their local caches
     */
    public void terminateSession(String sessionId, String terminatedBy) {
        SsoSession session = getSession(sessionId);
        if (session == null) {
            log.debug("SSO session {} not found, already terminated", sessionId);
            return;
        }

        // Remove from Redis
        redisTemplate.delete(SSO_SESSION_PREFIX + sessionId);
        redisTemplate.opsForSet().remove(
                SSO_USER_SESSIONS_PREFIX + session.userId, sessionId);

        // Publish logout event
        SsoLogoutEvent event = new SsoLogoutEvent(
                sessionId, session.userId, session.clientId,
                terminatedBy, Instant.now()
        );
        stringRedisTemplate.convertAndSend(SSO_LOGOUT_CHANNEL, toJson(event));

        log.info("SSO session terminated: sid={}, user={}, by={}",
                sessionId, session.userId, terminatedBy);
    }

    /**
     * Terminate all SSO sessions for a user (global logout).
     */
    public void terminateAllUserSessions(String userId, String terminatedBy) {
        List<SsoSession> sessions = getUserSessions(userId);
        for (SsoSession session : sessions) {
            terminateSession(session.sessionId, terminatedBy);
        }
    }

    /**
     * Register a local logout event listener.
     * Used for in-process handling (e.g., revoking tokens).
     */
    public void registerLogoutListener(String listenerId, Consumer<SsoSession> listener) {
        logoutListeners.put(listenerId, listener);
    }

    /**
     * Remove a logout listener.
     */
    public void unregisterLogoutListener(String listenerId) {
        logoutListeners.remove(listenerId);
    }

    // ========================================================================
    // Redis Pub/Sub Message Listener
    // ========================================================================

    private class SsoLogoutMessageListener implements MessageListener {
        @Override
        public void onMessage(Message message, byte[] pattern) {
            try {
                String body = new String(message.getBody(), StandardCharsets.UTF_8);
                SsoLogoutEvent event = fromJsonLogout(body);
                log.debug("Received SSO logout event: sid={}, user={}",
                        event.sessionId, event.userId);

                // Notify local listeners
                SsoSession session = getSession(event.sessionId);
                if (session == null) {
                    // Session already removed, create minimal object for notification
                    session = new SsoSession(event.sessionId, event.userId, null,
                            event.clientId, null, null, null, null, 0);
                }
                for (Consumer<SsoSession> listener : logoutListeners.values()) {
                    try {
                        listener.accept(session);
                    } catch (Exception e) {
                        log.error("Error in SSO logout listener", e);
                    }
                }
            } catch (Exception e) {
                log.error("Failed to handle SSO logout message", e);
            }
        }
    }

    // ========================================================================
    // Serialization
    // ========================================================================

    private String toJson(Object obj) {
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Failed to serialize SSO session", e);
        }
    }

    private SsoSession fromJson(String json) throws JsonProcessingException {
        return objectMapper.readValue(json, SsoSession.class);
    }

    private SsoLogoutEvent fromJsonLogout(String json) throws JsonProcessingException {
        return objectMapper.readValue(json, SsoLogoutEvent.class);
    }

    // ========================================================================
    // Data classes
    // ========================================================================

    public record SsoSession(
            String sessionId,
            String userId,
            String email,
            String clientId,
            String ipAddress,
            String userAgent,
            Instant createdAt,
            Instant lastActivityAt,
            long ttlSeconds
    ) {}

    public record SsoLogoutEvent(
            String sessionId,
            String userId,
            String clientId,
            String terminatedBy,
            Instant terminatedAt
    ) {}
}
