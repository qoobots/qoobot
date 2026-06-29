package com.qoobot.qooauth.auth.controller;

import com.nimbusds.jwt.JWTClaimsSet;
import com.qoobot.qooauth.auth.security.JwtTokenProvider;
import com.qoobot.qooauth.auth.service.SsoSessionService;
import com.qoobot.qooauth.auth.service.SsoSessionService.SsoSession;
import com.qoobot.qooauth.auth.service.TokenService;
import com.qoobot.qooauth.common.dto.ApiResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.*;

/**
 * SSO (Single Sign-On) controller.
 * Provides SSO session management and Token Introspection (RFC 7662).
 */
@RestController
@RequestMapping("/api/v1/auth/sso")
public class SsoController {

    private static final Logger log = LoggerFactory.getLogger(SsoController.class);

    private final SsoSessionService ssoSessionService;
    private final JwtTokenProvider jwtTokenProvider;
    private final TokenService tokenService;

    public SsoController(SsoSessionService ssoSessionService,
                          JwtTokenProvider jwtTokenProvider,
                          TokenService tokenService) {
        this.ssoSessionService = ssoSessionService;
        this.jwtTokenProvider = jwtTokenProvider;
        this.tokenService = tokenService;
    }

    // ========================================================================
    // SSO Session Management
    // ========================================================================

    /**
     * GET /api/v1/auth/sso/sessions
     * List all active SSO sessions for the authenticated user.
     */
    @GetMapping("/sessions")
    public ResponseEntity<ApiResponse<List<Map<String, Object>>>> listSessions(
            @RequestAttribute("userId") String userId) {

        List<SsoSession> sessions = ssoSessionService.getUserSessions(userId);
        List<Map<String, Object>> result = new ArrayList<>();
        for (SsoSession s : sessions) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("session_id", s.sessionId());
            m.put("client_id", s.clientId());
            m.put("ip_address", s.ipAddress());
            m.put("user_agent", s.userAgent());
            m.put("created_at", s.createdAt().toString());
            m.put("last_activity_at", s.lastActivityAt().toString());
            m.put("ttl_seconds", s.ttlSeconds());
            result.add(m);
        }

        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    /**
     * DELETE /api/v1/auth/sso/sessions/{sessionId}
     * Terminate a specific SSO session (logout from one device).
     */
    @DeleteMapping("/sessions/{sessionId}")
    public ResponseEntity<ApiResponse<Map<String, Object>>> terminateSession(
            @RequestAttribute("userId") String userId,
            @PathVariable String sessionId) {

        SsoSession session = ssoSessionService.getSession(sessionId);
        if (session == null || !session.userId().equals(userId)) {
            return ResponseEntity.status(404)
                    .body(ApiResponse.error("NOT_FOUND", "SSO session not found"));
        }

        ssoSessionService.terminateSession(sessionId, userId);
        return ResponseEntity.ok(ApiResponse.ok(Map.of(
                "session_id", sessionId,
                "terminated", true
        )));
    }

    /**
     * DELETE /api/v1/auth/sso/sessions
     * Terminate all SSO sessions except current (or all if logout_all=true).
     */
    @DeleteMapping("/sessions")
    public ResponseEntity<ApiResponse<Map<String, Object>>> terminateAllSessions(
            @RequestAttribute("userId") String userId,
            @RequestParam(value = "current_sid", required = false) String currentSid,
            @RequestParam(value = "logout_all", defaultValue = "false") boolean logoutAll) {

        if (logoutAll) {
            ssoSessionService.terminateAllUserSessions(userId, userId);
        } else {
            List<SsoSession> sessions = ssoSessionService.getUserSessions(userId);
            for (SsoSession s : sessions) {
                if (!s.sessionId().equals(currentSid)) {
                    ssoSessionService.terminateSession(s.sessionId(), userId);
                }
            }
        }

        return ResponseEntity.ok(ApiResponse.ok(Map.of(
                "message", "Sessions terminated",
                "logout_all", logoutAll
        )));
    }

    /**
     * POST /api/v1/auth/sso/sessions/{sessionId}/refresh
     * Refresh an SSO session (extend TTL).
     */
    @PostMapping("/sessions/{sessionId}/refresh")
    public ResponseEntity<ApiResponse<Map<String, Object>>> refreshSession(
            @RequestAttribute("userId") String userId,
            @PathVariable String sessionId) {

        boolean refreshed = ssoSessionService.refreshSession(sessionId);
        if (!refreshed) {
            return ResponseEntity.status(404)
                    .body(ApiResponse.error("NOT_FOUND", "SSO session not found or expired"));
        }

        return ResponseEntity.ok(ApiResponse.ok(Map.of(
                "session_id", sessionId,
                "refreshed", true
        )));
    }

    // ========================================================================
    // Token Introspection (RFC 7662)
    // ========================================================================

    /**
     * POST /api/v1/auth/sso/introspect
     * Token introspection endpoint per RFC 7662.
     * Allows resource servers to validate tokens and get metadata.
     *
     * Request: application/x-www-form-urlencoded
     *   token=<access_token>
     *   token_type_hint=access_token (optional)
     *
     * Response: JSON with "active" boolean and token metadata.
     */
    @PostMapping(value = "/introspect", consumes = "application/x-www-form-urlencoded")
    public ResponseEntity<Map<String, Object>> introspect(
            @RequestParam("token") String token,
            @RequestParam(value = "token_type_hint", required = false) String tokenTypeHint) {

        Map<String, Object> result = new LinkedHashMap<>();

        try {
            JWTClaimsSet claims = jwtTokenProvider.verifyAccessToken(token);

            result.put("active", true);
            result.put("scope", claims.getStringClaim("scope"));
            result.put("client_id", "qoobot_api");
            result.put("username", claims.getSubject());
            result.put("token_type", "Bearer");
            result.put("exp", claims.getExpirationTime().toInstant().getEpochSecond());
            result.put("iat", claims.getIssueTime().toInstant().getEpochSecond());
            result.put("sub", claims.getSubject());
            result.put("iss", claims.getIssuer());
            result.put("jti", claims.getJWTID());

            // SSO claims
            String sid = claims.getStringClaim("sid");
            if (sid != null) {
                result.put("sid", sid);
                // Check if SSO session is still valid
                result.put("sso_session_active", ssoSessionService.isValidSession(sid));
            }

            Long authTime = claims.getLongClaim("auth_time");
            if (authTime != null) {
                result.put("auth_time", authTime);
            }

        } catch (Exception e) {
            result.put("active", false);
            log.debug("Token introspection failed: {}", e.getMessage());
        }

        return ResponseEntity.ok(result);
    }

    // ========================================================================
    // SSO Session Validation (for Gateway / Resource Servers)
    // ========================================================================

    /**
     * GET /api/v1/auth/sso/sessions/{sessionId}/validate
     * Check if an SSO session is still valid.
     * Used by API Gateway and resource servers for fast session validation.
     */
    @GetMapping("/sessions/{sessionId}/validate")
    public ResponseEntity<Map<String, Object>> validateSession(
            @PathVariable String sessionId) {

        boolean valid = ssoSessionService.isValidSession(sessionId);
        SsoSession session = valid ? ssoSessionService.getSession(sessionId) : null;

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("session_id", sessionId);
        result.put("valid", valid);

        if (session != null) {
            result.put("user_id", session.userId());
            result.put("email", session.email());
            result.put("client_id", session.clientId());
            result.put("last_activity_at", session.lastActivityAt().toString());
        }

        return ResponseEntity.ok(result);
    }
}
