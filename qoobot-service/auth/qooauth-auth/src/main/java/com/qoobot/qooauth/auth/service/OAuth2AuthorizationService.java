package com.qoobot.qooauth.auth.service;

import com.qoobot.qooauth.auth.entity.OAuth2AuthorizationCode;
import com.qoobot.qooauth.auth.entity.OAuth2Client;
import com.qoobot.qooauth.auth.entity.User;
import com.qoobot.qooauth.auth.repository.OAuth2AuthorizationCodeRepository;
import com.qoobot.qooauth.auth.repository.OAuth2ClientRepository;
import com.qoobot.qooauth.auth.repository.UserRepository;
import com.qoobot.qooauth.auth.security.JwtTokenProvider;
import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.common.util.IdGenerator;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;

/**
 * OAuth 2.0 / OIDC Authorization Service.
 * Implements Authorization Code flow with PKCE, Client Credentials, and Device Code.
 */
@Service
public class OAuth2AuthorizationService {

    private static final Duration AUTH_CODE_TTL = Duration.ofMinutes(10);

    private final OAuth2ClientRepository clientRepository;
    private final OAuth2AuthorizationCodeRepository authCodeRepository;
    private final UserRepository userRepository;
    private final JwtTokenProvider jwtTokenProvider;
    private final TokenService tokenService;
    private final SecureRandom secureRandom = new SecureRandom();

    public OAuth2AuthorizationService(OAuth2ClientRepository clientRepository,
                                       OAuth2AuthorizationCodeRepository authCodeRepository,
                                       UserRepository userRepository,
                                       JwtTokenProvider jwtTokenProvider,
                                       TokenService tokenService) {
        this.clientRepository = clientRepository;
        this.authCodeRepository = authCodeRepository;
        this.userRepository = userRepository;
        this.jwtTokenProvider = jwtTokenProvider;
        this.tokenService = tokenService;
    }

    /**
     * Validate an OAuth2 authorization request and generate an authorization code.
     * Used by the Authorization Endpoint after user authentication.
     */
    @Transactional
    public AuthorizationResult authorize(String clientId, String redirectUri,
                                          String responseType, String scope,
                                          String codeChallenge, String codeChallengeMethod,
                                          String state, String nonce, String userId) {

        // Validate client
        OAuth2Client client = clientRepository.findByClientIdAndEnabledTrue(clientId)
                .orElseThrow(() -> new AuthException(ErrorCodes.OAUTH_INVALID_CLIENT,
                        "Unknown or disabled client: " + clientId));

        // Validate redirect URI
        if (!isValidRedirectUri(client, redirectUri)) {
            throw new AuthException(ErrorCodes.OAUTH_INVALID_REDIRECT_URI,
                    "Redirect URI not registered for this client");
        }

        // Validate response_type (must be "code" for authorization_code flow)
        if (!"code".equals(responseType)) {
            throw new AuthException(ErrorCodes.OAUTH_UNSUPPORTED_RESPONSE_TYPE,
                    "Unsupported response_type: " + responseType);
        }

        // Validate scope
        String effectiveScope = validateAndFilterScopes(client, scope);

        // PKCE validation
        if (client.isRequirePkce() && (codeChallenge == null || codeChallenge.isEmpty())) {
            throw new AuthException(ErrorCodes.OAUTH_PKCE_REQUIRED,
                    "PKCE code_challenge is required for this client");
        }

        // Generate authorization code
        String code = IdGenerator.generateOAuthCode();
        OAuth2AuthorizationCode authCode = new OAuth2AuthorizationCode();
        authCode.setCode(code);
        authCode.setClientId(clientId);
        authCode.setUserId(userId);
        authCode.setRedirectUri(redirectUri);
        authCode.setScopes(effectiveScope);
        authCode.setCodeChallenge(codeChallenge);
        authCode.setCodeChallengeMethod(codeChallengeMethod != null ? codeChallengeMethod : "S256");
        authCode.setNonce(nonce);
        authCode.setState(state);
        authCode.setExpiresAt(Instant.now().plus(AUTH_CODE_TTL));
        authCode.setCreatedAt(Instant.now());
        authCodeRepository.save(authCode);

        return new AuthorizationResult(code, state, redirectUri);
    }

    /**
     * Exchange an authorization code for tokens (Token Endpoint — authorization_code grant).
     */
    @Transactional
    public TokenExchangeResult exchangeAuthorizationCode(String code, String redirectUri,
                                                          String codeVerifier, String clientId,
                                                          String clientSecret) {

        // Authenticate client
        OAuth2Client client = authenticateClient(clientId, clientSecret);

        // Find and validate authorization code
        OAuth2AuthorizationCode authCode = authCodeRepository
                .findByCodeAndUsedFalse(code)
                .orElseThrow(() -> new AuthException(ErrorCodes.OAUTH_INVALID_CODE,
                        "Invalid or expired authorization code"));

        // Check expiry
        if (Instant.now().isAfter(authCode.getExpiresAt())) {
            throw new AuthException(ErrorCodes.OAUTH_INVALID_CODE,
                    "Authorization code has expired");
        }

        // Verify client matches
        if (!authCode.getClientId().equals(clientId)) {
            throw new AuthException(ErrorCodes.OAUTH_INVALID_CLIENT,
                    "Client ID mismatch");
        }

        // Verify redirect URI matches
        if (!authCode.getRedirectUri().equals(redirectUri)) {
            throw new AuthException(ErrorCodes.OAUTH_INVALID_REDIRECT_URI,
                    "Redirect URI mismatch");
        }

        // PKCE verification
        if (authCode.getCodeChallenge() != null && !authCode.getCodeChallenge().isEmpty()) {
            if (codeVerifier == null || codeVerifier.isEmpty()) {
                throw new AuthException(ErrorCodes.OAUTH_PKCE_REQUIRED,
                        "code_verifier is required");
            }
            String computedChallenge = computeS256Challenge(codeVerifier);
            if (!computedChallenge.equals(authCode.getCodeChallenge())) {
                throw new AuthException(ErrorCodes.OAUTH_INVALID_CODE,
                        "PKCE verification failed: code_verifier does not match code_challenge");
            }
        }

        // Mark code as used
        authCode.setUsed(true);
        authCodeRepository.save(authCode);

        // Fetch user
        User user = userRepository.findById(authCode.getUserId())
                .orElseThrow(() -> new AuthException(ErrorCodes.USER_NOT_FOUND,
                        "User not found"));

        // Issue tokens
        TokenService.TokenPair tokens = tokenService.issueTokens(
                user.getUserId(), user.getEmail(),
                user.getNickname(), getAvatarUrl(user),
                authCode.getScopes());

        // Generate ID token if openid scope requested
        String idToken = null;
        if (authCode.getScopes().contains("openid")) {
            idToken = jwtTokenProvider.issueIdToken(
                    user.getUserId(), user.getEmail(),
                    user.getNickname(), getAvatarUrl(user));
        }

        return new TokenExchangeResult(
                tokens.accessToken(), tokens.refreshToken(), idToken,
                tokens.tokenType(), tokens.expiresIn(), authCode.getScopes());
    }

    /**
     * Client Credentials grant — machine-to-machine tokens.
     */
    public TokenExchangeResult clientCredentialsGrant(String clientId, String clientSecret, String scope) {
        OAuth2Client client = authenticateClient(clientId, clientSecret);

        // Validate client supports client_credentials grant
        if (!Arrays.asList(client.getGrantTypes().split(",")).contains("client_credentials")) {
            throw new AuthException(ErrorCodes.OAUTH_UNSUPPORTED_GRANT_TYPE,
                    "client_credentials grant not allowed for this client");
        }

        String effectiveScope = validateAndFilterScopes(client, scope);

        // Issue service-level access token (sub = client_id)
        String accessToken = jwtTokenProvider.issueServiceAccessToken(clientId, effectiveScope);

        return new TokenExchangeResult(
                accessToken, null, null, "Bearer", 3600, effectiveScope);
    }

    /**
     * Refresh token grant — exchange refresh token for new access token.
     */
    @Transactional
    public TokenExchangeResult refreshTokenGrant(String refreshToken, String clientId, String clientSecret) {
        // Authenticate client
        OAuth2Client client = authenticateClient(clientId, clientSecret);

        // Validate and consume refresh token
        String userId = jwtTokenProvider.validateRefreshToken(refreshToken);
        jwtTokenProvider.revokeRefreshToken(refreshToken);

        // Fetch user
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.USER_NOT_FOUND, "User not found"));

        // Issue new tokens
        TokenService.TokenPair tokens = tokenService.issueTokens(
                user.getUserId(), user.getEmail(),
                user.getNickname(), getAvatarUrl(user),
                "openid profile email");

        String idToken = jwtTokenProvider.issueIdToken(
                user.getUserId(), user.getEmail(),
                user.getNickname(), getAvatarUrl(user));

        return new TokenExchangeResult(
                tokens.accessToken(), tokens.refreshToken(), idToken,
                tokens.tokenType(), tokens.expiresIn(), "openid profile email");
    }

    /**
     * Get user info for an access token (UserInfo endpoint).
     */
    public UserInfoResult getUserInfo(String accessToken) {
        try {
            var claims = jwtTokenProvider.verifyAccessToken(accessToken);
            String userId = claims.getSubject();
            User user = userRepository.findById(userId)
                    .orElseThrow(() -> new AuthException(ErrorCodes.USER_NOT_FOUND, "User not found"));

            Map<String, Object> info = new LinkedHashMap<>();
            info.put("sub", user.getUserId());
            info.put("email", user.getEmail());
            info.put("email_verified", user.isEmailVerified());
            info.put("name", user.getNickname());
            if (getAvatarUrl(user) != null) {
                info.put("picture", getAvatarUrl(user));
            }
            info.put("locale", user.getLanguage());

            return new UserInfoResult(info);
        } catch (Exception e) {
            throw new AuthException(ErrorCodes.TOKEN_INVALID, "Invalid access token");
        }
    }

    /**
     * Register a new OAuth2 client (for developers integrating Sign in with QooBot).
     */
    @Transactional
    public OAuth2Client registerClient(String clientName, List<String> redirectUris,
                                        String grantTypes, String scopes,
                                        String tokenEndpointAuthMethod,
                                        String ownerUserId) {
        String clientId = IdGenerator.generateApiKeyId();
        String clientSecret = generateClientSecret();

        OAuth2Client client = new OAuth2Client();
        client.setClientId(clientId);
        client.setClientSecret(clientSecret);
        client.setClientName(clientName);
        client.setRedirectUris(toJsonArray(redirectUris));
        client.setGrantTypes(grantTypes != null ? grantTypes : "authorization_code,refresh_token");
        client.setScopes(scopes != null ? scopes : "openid profile email");
        client.setTokenEndpointAuthMethod(
                tokenEndpointAuthMethod != null ? tokenEndpointAuthMethod : "client_secret_basic");
        client.setRequirePkce(true);
        client.setOwnerUserId(ownerUserId);
        client.setCreatedAt(Instant.now());
        client.setUpdatedAt(Instant.now());

        return clientRepository.save(client);
    }

    // --- Private helpers ---

    private OAuth2Client authenticateClient(String clientId, String clientSecret) {
        OAuth2Client client = clientRepository.findByClientIdAndEnabledTrue(clientId)
                .orElseThrow(() -> new AuthException(ErrorCodes.OAUTH_INVALID_CLIENT,
                        "Unknown or disabled client"));

        if (clientSecret == null || !clientSecret.equals(client.getClientSecret())) {
            throw new AuthException(ErrorCodes.OAUTH_INVALID_CLIENT,
                    "Invalid client credentials");
        }

        return client;
    }

    private boolean isValidRedirectUri(OAuth2Client client, String redirectUri) {
        if (redirectUri == null) return false;
        String[] uris = client.getRedirectUris()
                .replaceAll("[\\[\\]\"]", "")
                .split(",");
        for (String uri : uris) {
            if (uri.trim().equals(redirectUri)) return true;
        }
        return false;
    }

    private String validateAndFilterScopes(OAuth2Client client, String requestedScope) {
        if (requestedScope == null || requestedScope.isEmpty()) {
            return "openid";  // default minimum
        }
        Set<String> allowed = new HashSet<>(
                Arrays.asList(client.getScopes().split(" ")));
        Set<String> requested = new HashSet<>(Arrays.asList(requestedScope.split(" ")));
        requested.retainAll(allowed);
        if (requested.isEmpty()) {
            return "openid";
        }
        return String.join(" ", requested);
    }

    private String computeS256Challenge(String codeVerifier) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(codeVerifier.getBytes(StandardCharsets.US_ASCII));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(digest);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }

    private String generateClientSecret() {
        byte[] bytes = new byte[32];
        secureRandom.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private String getAvatarUrl(User user) {
        return user.getAvatarHash() != null
                ? "https://cdn.qoobot.com/avatars/" + user.getAvatarHash()
                : null;
    }

    private String toJsonArray(List<String> items) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < items.size(); i++) {
            if (i > 0) sb.append(",");
            sb.append("\"").append(items.get(i)).append("\"");
        }
        sb.append("]");
        return sb.toString();
    }

    // --- DTOs ---

    public record AuthorizationResult(String code, String state, String redirectUri) {}

    public record TokenExchangeResult(
            String accessToken, String refreshToken, String idToken,
            String tokenType, long expiresIn, String scope
    ) {}

    public record UserInfoResult(Map<String, Object> claims) {}
}
