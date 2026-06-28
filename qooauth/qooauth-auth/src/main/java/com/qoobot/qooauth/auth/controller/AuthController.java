package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.dto.LoginRequest;
import com.qoobot.qooauth.auth.dto.RegisterRequest;
import com.qoobot.qooauth.auth.dto.TokenResponse;
import com.qoobot.qooauth.auth.service.AuthService;
import com.qoobot.qooauth.auth.service.AuthService.LoginResult;
import com.qoobot.qooauth.auth.service.AuthService.RegisterResult;
import com.qoobot.qooauth.auth.service.RateLimitService;
import com.qoobot.qooauth.common.dto.ApiResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService authService;
    private final RateLimitService rateLimitService;

    public AuthController(AuthService authService, RateLimitService rateLimitService) {
        this.authService = authService;
        this.rateLimitService = rateLimitService;
    }

    /**
     * Register a new QooBot ID account.
     */
    @PostMapping("/register")
    public ResponseEntity<ApiResponse<RegisterResult>> register(
            @Valid @RequestBody RegisterRequest request) {

        rateLimitService.checkApiRateLimit("global", "register");

        RegisterResult result = authService.register(
                request.email(), request.password(), request.nickname(),
                request.language(), request.acceptTos());

        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.ok(result));
    }

    /**
     * Login with email and password.
     */
    @PostMapping("/login")
    public ResponseEntity<ApiResponse<TokenResponse>> login(
            @Valid @RequestBody LoginRequest request,
            HttpServletRequest httpRequest) {

        String ip = getClientIp(httpRequest);
        String userAgent = httpRequest.getHeader("User-Agent");
        String deviceFingerprint = httpRequest.getHeader("X-Device-Fingerprint");

        LoginResult result = authService.login(
                request.email(), request.password(),
                deviceFingerprint, "qoobot_api", ip, userAgent);

        if (result.requiresMfa()) {
            return ResponseEntity.ok(
                    ApiResponse.ok(TokenResponse.mfaRequired(
                            result.mfaToken(), result.mfaMethods())));
        }

        return ResponseEntity.ok(
                ApiResponse.ok(TokenResponse.fromTokenPair(result.tokens(), result.user())));
    }

    /**
     * Logout current session.
     */
    @PostMapping("/logout")
    public ResponseEntity<Void> logout(
            @RequestHeader("Authorization") String authorization,
            @RequestBody(required = false) Map<String, Boolean> body) {

        String accessToken = extractBearerToken(authorization);
        boolean logoutAll = body != null && body.getOrDefault("logout_all_devices", false);

        // User ID would come from SecurityContext in production
        authService.logout("current_user", accessToken, null, logoutAll);
        return ResponseEntity.noContent().build();
    }

    /**
     * Refresh access token.
     */
    @PostMapping("/refresh")
    public ResponseEntity<ApiResponse<TokenResponse>> refresh(
            @RequestBody Map<String, String> body) {

        String refreshToken = body.get("refresh_token");
        if (refreshToken == null || refreshToken.isEmpty()) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error("BAD_REQUEST", "refresh_token is required"));
        }

        var tokens = authService.refreshToken(refreshToken, null, null, null);
        return ResponseEntity.ok(
                ApiResponse.ok(TokenResponse.fromTokenPair(tokens, null)));
    }

    // --- Helpers ---

    private String extractBearerToken(String authorization) {
        if (authorization != null && authorization.startsWith("Bearer ")) {
            return authorization.substring(7);
        }
        return null;
    }

    private String getClientIp(HttpServletRequest request) {
        String xForwardedFor = request.getHeader("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
