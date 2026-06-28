package com.qoobot.qooauth.auth.service;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jwt.JWTClaimsSet;
import com.qoobot.qooauth.auth.security.JwtTokenProvider;
import org.springframework.stereotype.Service;

import java.text.ParseException;
import java.time.Instant;

/**
 * Token lifecycle management service.
 * Handles issuance, verification, refresh, and revocation.
 */
@Service
public class TokenService {

    private final JwtTokenProvider jwtTokenProvider;

    public TokenService(JwtTokenProvider jwtTokenProvider) {
        this.jwtTokenProvider = jwtTokenProvider;
    }

    /**
     * Issue a new token pair (access + refresh + id) for a user.
     */
    public TokenPair issueTokens(String userId, String email, String nickname, String avatarUrl, String scope) {
        return issueTokens(userId, email, nickname, avatarUrl, scope, null, null);
    }

    /**
     * Issue a new token pair with SSO session context.
     */
    public TokenPair issueTokens(String userId, String email, String nickname, String avatarUrl,
                                  String scope, String sessionId, Instant authTime) {
        String accessToken = jwtTokenProvider.issueAccessToken(userId, scope, sessionId, authTime);
        String refreshToken = jwtTokenProvider.issueRefreshToken(userId);
        String idToken = jwtTokenProvider.issueIdToken(userId, email, nickname, avatarUrl, authTime);

        return new TokenPair(accessToken, refreshToken, idToken, "Bearer", 3600);
    }

    /**
     * Verify an access token and return its claims.
     */
    public JWTClaimsSet verifyToken(String token) throws ParseException, JOSEException {
        return jwtTokenProvider.verifyAccessToken(token);
    }

    /**
     * Refresh tokens: validate refresh token and issue new pair.
     */
    public TokenPair refreshTokens(String refreshToken, String email, String nickname, String avatarUrl, String scope) {
        String userId = jwtTokenProvider.validateRefreshToken(refreshToken);
        // Invalidate old refresh token
        jwtTokenProvider.revokeRefreshToken(refreshToken);
        // Issue new pair
        return issueTokens(userId, email, nickname, avatarUrl, scope);
    }

    /**
     * Revoke all tokens for a user session.
     */
    public void revokeTokens(String accessToken, String refreshToken) {
        if (accessToken != null) {
            jwtTokenProvider.revokeAccessToken(accessToken);
        }
        if (refreshToken != null) {
            jwtTokenProvider.revokeRefreshToken(refreshToken);
        }
    }

    /**
     * Verify an MFA pending token and return its claims.
     * MFA tokens are access tokens with scope "mfa_pending".
     */
    public JWTClaimsSet verifyMfaToken(String mfaToken) {
        try {
            JWTClaimsSet claims = jwtTokenProvider.verifyAccessToken(mfaToken);
            String scope = claims.getStringClaim("scope");
            if (scope == null || !scope.contains("mfa_pending")) {
                throw new com.qoobot.qooauth.common.exception.AuthException(
                        com.qoobot.qooauth.common.constants.ErrorCodes.TOKEN_INVALID,
                        "Not a valid MFA session token");
            }
            return claims;
        } catch (java.text.ParseException | com.nimbusds.jose.JOSEException e) {
            throw new com.qoobot.qooauth.common.exception.AuthException(
                    com.qoobot.qooauth.common.constants.ErrorCodes.TOKEN_INVALID,
                    "Invalid MFA token: " + e.getMessage());
        }
    }

    public record TokenPair(
            String accessToken,
            String refreshToken,
            String idToken,
            String tokenType,
            long expiresIn
    ) {}
}
