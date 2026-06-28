package com.qoobot.qooauth.auth.security;

import com.nimbusds.jose.*;
import com.nimbusds.jose.crypto.MACSigner;
import com.nimbusds.jose.crypto.MACVerifier;
import com.nimbusds.jose.jwk.OctetKeyPair;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import com.qoobot.qooauth.common.enums.TokenType;
import com.qoobot.qooauth.common.exception.TokenExpiredException;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import java.security.SecureRandom;
import java.text.ParseException;
import java.time.Duration;
import java.time.Instant;
import java.util.Date;
import java.util.UUID;

/**
 * JWT Token provider using Ed25519 for signing.
 * Access tokens: short-lived (1h), Ed25519 signed.
 * Refresh tokens: longer-lived (30d), HMAC-SHA256 signed, stored in Redis.
 */
@Component
public class JwtTokenProvider {

    private static final Duration ACCESS_TOKEN_TTL = Duration.ofHours(1);
    private static final Duration REFRESH_TOKEN_TTL = Duration.ofDays(30);
    private static final Duration ID_TOKEN_TTL = Duration.ofMinutes(10);

    private final OctetKeyPair ed25519Key;
    private final JWSSigner ed25519Signer;
    private final JWSVerifier ed25519Verifier;
    private final SecretKey refreshTokenKey;
    private final RedisTemplate<String, String> redisTemplate;

    public JwtTokenProvider(OctetKeyPair ed25519Key, RedisTemplate<String, String> redisTemplate) throws JOSEException {
        this.ed25519Key = ed25519Key;
        this.ed25519Signer = new com.nimbusds.jose.crypto.Ed25519Signer(ed25519Key);
        this.ed25519Verifier = new com.nimbusds.jose.crypto.Ed25519Verifier(ed25519Key.toPublicJWK());
        this.redisTemplate = redisTemplate;

        // Generate random key for refresh tokens (ephemeral per instance)
        byte[] keyBytes = new byte[32];
        new SecureRandom().nextBytes(keyBytes);
        this.refreshTokenKey = new SecretKeySpec(keyBytes, "HmacSHA256");
    }

    /**
     * Issue an access token for a user.
     */
    public String issueAccessToken(String userId, String scope) {
        try {
            Instant now = Instant.now();
            Instant expires = now.plus(ACCESS_TOKEN_TTL);

            JWTClaimsSet claims = new JWTClaimsSet.Builder()
                    .subject(userId)
                    .issuer("https://id.qoobot.com")
                    .issueTime(Date.from(now))
                    .expirationTime(Date.from(expires))
                    .jwtID(UUID.randomUUID().toString())
                    .claim("type", TokenType.ACCESS.name())
                    .claim("scope", scope)
                    .build();

            SignedJWT jwt = new SignedJWT(
                    new JWSHeader.Builder(JWSAlgorithm.EdDSA)
                            .keyID(ed25519Key.getKeyID())
                            .build(),
                    claims);
            jwt.sign(ed25519Signer);
            return jwt.serialize();
        } catch (JOSEException e) {
            throw new RuntimeException("Failed to issue access token", e);
        }
    }

    /**
     * Issue a refresh token (opaque, stored in Redis).
     */
    public String issueRefreshToken(String userId) {
        String token = UUID.randomUUID().toString() + "." + UUID.randomUUID().toString();
        String redisKey = "qooauth:refresh_token:" + token;
        redisTemplate.opsForValue().set(redisKey, userId, REFRESH_TOKEN_TTL);
        return token;
    }

    /**
     * Issue an ID token (OIDC).
     */
    public String issueIdToken(String userId, String email, String nickname, String avatarUrl) {
        try {
            Instant now = Instant.now();
            Instant expires = now.plus(ID_TOKEN_TTL);

            JWTClaimsSet claims = new JWTClaimsSet.Builder()
                    .subject(userId)
                    .issuer("https://id.qoobot.com")
                    .audience("qoobot")
                    .issueTime(Date.from(now))
                    .expirationTime(Date.from(expires))
                    .jwtID(UUID.randomUUID().toString())
                    .claim("email", email)
                    .claim("name", nickname)
                    .claim("picture", avatarUrl)
                    .build();

            SignedJWT jwt = new SignedJWT(
                    new JWSHeader.Builder(JWSAlgorithm.EdDSA)
                            .keyID(ed25519Key.getKeyID())
                            .build(),
                    claims);
            jwt.sign(ed25519Signer);
            return jwt.serialize();
        } catch (JOSEException e) {
            throw new RuntimeException("Failed to issue ID token", e);
        }
    }

    /**
     * Verify and parse an access token.
     * Also checks token blacklist in Redis.
     */
    public JWTClaimsSet verifyAccessToken(String token) throws ParseException, JOSEException {
        SignedJWT jwt = SignedJWT.parse(token);

        // Check blacklist
        String jti = jwt.getJWTClaimsSet().getJWTID();
        if (Boolean.TRUE.equals(redisTemplate.hasKey("qooauth:token_blacklist:" + jti))) {
            throw new TokenExpiredException("Token has been revoked");
        }

        if (!jwt.verify(ed25519Verifier)) {
            throw new JOSEException("Invalid token signature");
        }

        JWTClaimsSet claims = jwt.getJWTClaimsSet();
        Instant expiration = claims.getExpirationTime().toInstant();
        if (Instant.now().isAfter(expiration)) {
            throw new TokenExpiredException();
        }

        return claims;
    }

    /**
     * Validate refresh token and return the associated user ID.
     */
    public String validateRefreshToken(String refreshToken) {
        String redisKey = "qooauth:refresh_token:" + refreshToken;
        String userId = redisTemplate.opsForValue().get(redisKey);
        if (userId == null) {
            throw new TokenExpiredException("Refresh token is invalid or expired");
        }
        return userId;
    }

    /**
     * Revoke an access token by adding it to the blacklist.
     */
    public void revokeAccessToken(String token) {
        try {
            SignedJWT jwt = SignedJWT.parse(token);
            String jti = jwt.getJWTClaimsSet().getJWTID();
            Instant expiration = jwt.getJWTClaimsSet().getExpirationTime().toInstant();
            Duration ttl = Duration.between(Instant.now(), expiration);
            if (!ttl.isNegative()) {
                redisTemplate.opsForValue().set(
                        "qooauth:token_blacklist:" + jti, "revoked", ttl);
            }
        } catch (ParseException e) {
            // Token unparseable, nothing to revoke
        }
    }

    /**
     * Issue a service-level access token for client_credentials grant.
     * The subject is the client_id, representing the service account.
     */
    public String issueServiceAccessToken(String clientId, String scope) {
        try {
            Instant now = Instant.now();
            Instant expires = now.plus(ACCESS_TOKEN_TTL);

            JWTClaimsSet claims = new JWTClaimsSet.Builder()
                    .subject(clientId)
                    .issuer("https://id.qoobot.com")
                    .issueTime(Date.from(now))
                    .expirationTime(Date.from(expires))
                    .jwtID(UUID.randomUUID().toString())
                    .claim("type", TokenType.ACCESS.name())
                    .claim("scope", scope)
                    .claim("client_id", clientId)
                    .build();

            SignedJWT jwt = new SignedJWT(
                    new JWSHeader.Builder(JWSAlgorithm.EdDSA)
                            .keyID(ed25519Key.getKeyID())
                            .build(),
                    claims);
            jwt.sign(ed25519Signer);
            return jwt.serialize();
        } catch (JOSEException e) {
            throw new RuntimeException("Failed to issue service access token", e);
        }
    }

    /**
     * Revoke a refresh token.
     */
    public void revokeRefreshToken(String refreshToken) {
        redisTemplate.delete("qooauth:refresh_token:" + refreshToken);
    }
}
