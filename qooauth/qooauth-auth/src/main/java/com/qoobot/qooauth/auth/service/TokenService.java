package com.qoobot.qooauth.auth.service;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jwt.JWTClaimsSet;
import com.qoobot.qooauth.auth.security.JwtTokenProvider;
import org.springframework.stereotype.Service;

import java.text.ParseException;

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
        String accessToken = jwtTokenProvider.issueAccessToken(userId, scope);
        String refreshToken = jwtTokenProvider.issueRefreshToken(userId);
        String idToken = jwtTokenProvider.issueIdToken(userId, email, nickname, avatarUrl);

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

    public record TokenPair(
            String accessToken,
            String refreshToken,
            String idToken,
            String tokenType,
            long expiresIn
    ) {}
}
