package com.qoobot.qooauth.auth.controller;

import com.nimbusds.jose.jwk.JWKSet;
import com.nimbusds.jose.jwk.OctetKeyPair;
import com.qoobot.qooauth.auth.entity.OAuth2Client;
import com.qoobot.qooauth.auth.service.OAuth2AuthorizationService;
import com.qoobot.qooauth.auth.service.OAuth2AuthorizationService.*;
import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.dto.ApiResponse;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.util.List;
import java.util.Map;

/**
 * OAuth 2.0 / OIDC Provider endpoints.
 *
 * Endpoints:
 *   GET  /oauth2/authorize  — Authorization endpoint
 *   POST /oauth2/token       — Token endpoint
 *   GET  /oauth2/userinfo    — UserInfo endpoint (OIDC)
 *   GET  /oauth2/jwks        — JWKS endpoint
 *   POST /oauth2/register    — Dynamic Client Registration
 */
@RestController
@RequestMapping("/oauth2")
public class OAuth2Controller {

    private final OAuth2AuthorizationService authorizationService;
    private final OctetKeyPair ed25519Key;

    public OAuth2Controller(OAuth2AuthorizationService authorizationService,
                            OctetKeyPair ed25519Key) {
        this.authorizationService = authorizationService;
        this.ed25519Key = ed25519Key;
    }

    /**
     * Authorization Endpoint.
     * GET /oauth2/authorize?response_type=code&client_id=...&redirect_uri=...&scope=...&state=...&code_challenge=...&code_challenge_method=S256&nonce=...
     *
     * In production, this would render a consent page. For now, we assume the user
     * is already authenticated (via session cookie or Bearer token in Authorization header)
     * and directly issue the authorization code.
     */
    @GetMapping("/authorize")
    public ResponseEntity<Void> authorize(
            @RequestParam("response_type") String responseType,
            @RequestParam("client_id") String clientId,
            @RequestParam("redirect_uri") String redirectUri,
            @RequestParam(required = false) String scope,
            @RequestParam(required = false) String state,
            @RequestParam(required = false, name = "code_challenge") String codeChallenge,
            @RequestParam(required = false, name = "code_challenge_method") String codeChallengeMethod,
            @RequestParam(required = false) String nonce,
            @RequestHeader(value = "X-Authenticated-User-Id", required = false) String authenticatedUserId) {

        // In production, user authentication would be handled by the session.
        // For API-driven flows, the caller provides the authenticated user ID via header.
        if (authenticatedUserId == null || authenticatedUserId.isEmpty()) {
            // Redirect to login — for now return 401 with redirect hint
            String loginUrl = "https://id.qoobot.com/login?redirect=" +
                    java.net.URLEncoder.encode(
                            "/oauth2/authorize?response_type=" + responseType +
                            "&client_id=" + clientId +
                            "&redirect_uri=" + java.net.URLEncoder.encode(redirectUri) +
                            "&scope=" + (scope != null ? scope : "") +
                            "&state=" + (state != null ? state : ""),
                            java.nio.charset.StandardCharsets.UTF_8);
            return ResponseEntity.status(302)
                    .location(URI.create(loginUrl))
                    .build();
        }

        AuthorizationResult result = authorizationService.authorize(
                clientId, redirectUri, responseType, scope,
                codeChallenge, codeChallengeMethod, state, nonce,
                authenticatedUserId);

        // Build redirect URI with code and state
        StringBuilder location = new StringBuilder(result.redirectUri());
        location.append("?code=").append(result.code());
        if (result.state() != null && !result.state().isEmpty()) {
            location.append("&state=").append(result.state());
        }

        return ResponseEntity.status(302)
                .location(URI.create(location.toString()))
                .build();
    }

    /**
     * Token Endpoint.
     * POST /oauth2/token
     *
     * Supports grant_type: authorization_code, client_credentials, refresh_token.
     * Client authentication: client_secret_basic (Authorization: Basic base64(client_id:client_secret))
     * or client_secret_post (client_id + client_secret in body).
     */
    @PostMapping("/token")
    public ResponseEntity<ApiResponse<Map<String, Object>>> token(
            @RequestParam("grant_type") String grantType,
            @RequestParam(required = false) String code,
            @RequestParam(required = false, name = "redirect_uri") String redirectUri,
            @RequestParam(required = false, name = "code_verifier") String codeVerifier,
            @RequestParam(required = false, name = "refresh_token") String refreshToken,
            @RequestParam(required = false) String scope,
            @RequestParam(required = false, name = "client_id") String clientIdBody,
            @RequestParam(required = false, name = "client_secret") String clientSecretBody,
            @RequestHeader(value = "Authorization", required = false) String authorizationHeader) {

        // Extract client credentials
        String clientId;
        String clientSecret;

        if (authorizationHeader != null && authorizationHeader.startsWith("Basic ")) {
            // client_secret_basic
            String[] creds = extractBasicCredentials(authorizationHeader);
            clientId = creds[0];
            clientSecret = creds[1];
        } else if (clientIdBody != null && clientSecretBody != null) {
            // client_secret_post
            clientId = clientIdBody;
            clientSecret = clientSecretBody;
        } else {
            return ResponseEntity.status(401)
                    .body(ApiResponse.error(ErrorCodes.OAUTH_INVALID_CLIENT, "Client authentication required"));
        }

        try {
            TokenExchangeResult result = switch (grantType) {
                case "authorization_code" -> {
                    if (code == null || redirectUri == null) {
                        throw new IllegalArgumentException("code and redirect_uri are required for authorization_code grant");
                    }
                    yield authorizationService.exchangeAuthorizationCode(
                            code, redirectUri, codeVerifier, clientId, clientSecret);
                }
                case "client_credentials" ->
                        authorizationService.clientCredentialsGrant(clientId, clientSecret, scope);
                case "refresh_token" -> {
                    if (refreshToken == null) {
                        throw new IllegalArgumentException("refresh_token is required for refresh_token grant");
                    }
                    yield authorizationService.refreshTokenGrant(refreshToken, clientId, clientSecret);
                }
                default -> throw new IllegalArgumentException("Unsupported grant_type: " + grantType);
            };

            Map<String, Object> body = new java.util.LinkedHashMap<>();
            body.put("access_token", result.accessToken());
            body.put("token_type", result.tokenType());
            body.put("expires_in", result.expiresIn());
            body.put("scope", result.scope());
            if (result.refreshToken() != null) {
                body.put("refresh_token", result.refreshToken());
            }
            if (result.idToken() != null) {
                body.put("id_token", result.idToken());
            }

            return ResponseEntity.ok(ApiResponse.ok(body));

        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error(ErrorCodes.OAUTH_INVALID_GRANT, e.getMessage()));
        }
    }

    /**
     * UserInfo Endpoint (OIDC).
     * GET /oauth2/userinfo
     * Bearer token authentication.
     */
    @GetMapping("/userinfo")
    public ResponseEntity<?> userInfo(
            @RequestHeader(value = "Authorization", required = false) String authorization) {

        if (authorization == null || !authorization.startsWith("Bearer ")) {
            return ResponseEntity.status(401)
                    .body(ApiResponse.error("AUTH_1008", "Bearer token required"));
        }

        String accessToken = authorization.substring(7);
        UserInfoResult result = authorizationService.getUserInfo(accessToken);
        return ResponseEntity.ok(result.claims());
    }

    /**
     * JWKS Endpoint.
     * GET /oauth2/jwks
     * Returns the public keys for token verification.
     */
    @GetMapping("/jwks")
    public ResponseEntity<Map<String, Object>> jwks() {
        JWKSet jwkSet = new JWKSet(ed25519Key.toPublicJWK());
        return ResponseEntity.ok(jwkSet.toJSONObject());
    }

    /**
     * Dynamic Client Registration.
     * POST /oauth2/register
     *
     * Allows developers to programmatically register OAuth2 clients.
     */
    @PostMapping("/register")
    public ResponseEntity<ApiResponse<Map<String, Object>>> registerClient(
            @RequestBody Map<String, Object> body,
            @RequestHeader(value = "X-Authenticated-User-Id", required = false) String authenticatedUserId) {

        String clientName = (String) body.getOrDefault("client_name", "Unnamed Client");
        @SuppressWarnings("unchecked")
        List<String> redirectUris = (List<String>) body.get("redirect_uris");
        String grantTypes = (String) body.get("grant_types");
        String scopes = (String) body.get("scope");
        String tokenEndpointAuthMethod = (String) body.get("token_endpoint_auth_method");

        if (redirectUris == null || redirectUris.isEmpty()) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error("GEN_9004", "redirect_uris is required"));
        }

        OAuth2Client client = authorizationService.registerClient(
                clientName, redirectUris, grantTypes, scopes,
                tokenEndpointAuthMethod, authenticatedUserId);

        Map<String, Object> result = new java.util.LinkedHashMap<>();
        result.put("client_id", client.getClientId());
        result.put("client_secret", client.getClientSecret());
        result.put("client_name", client.getClientName());
        result.put("redirect_uris", redirectUris);
        result.put("grant_types", client.getGrantTypes());
        result.put("token_endpoint_auth_method", client.getTokenEndpointAuthMethod());
        result.put("client_id_issued_at", client.getCreatedAt().getEpochSecond());

        return ResponseEntity.status(201).body(ApiResponse.ok(result));
    }

    // --- Helpers ---

    private String[] extractBasicCredentials(String authorizationHeader) {
        String base64 = authorizationHeader.substring(6);
        String decoded = new String(java.util.Base64.getDecoder().decode(base64));
        int colonIdx = decoded.indexOf(':');
        if (colonIdx < 0) {
            throw new IllegalArgumentException("Invalid Basic auth header");
        }
        return new String[] {
                decoded.substring(0, colonIdx),
                decoded.substring(colonIdx + 1)
        };
    }
}
