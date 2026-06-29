package com.qoobot.qoogear.common.security;

import io.jsonwebtoken.*;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.util.*;

/**
 * JWT Token provider — validates tokens issued by qooauth.
 * qoogear services trust qooauth-issued JWTs via shared signing key.
 */
@Slf4j
@Component
public class JwtTokenProvider {

    private final SecretKey key;
    private final long accessExpirationMs;
    private final long refreshExpirationMs;

    public JwtTokenProvider(
            @Value("${qoogear.security.jwt.secret:}") String secret,
            @Value("${qoogear.security.jwt.access-expiration-ms:900000}") long accessExpirationMs,
            @Value("${qoogear.security.jwt.refresh-expiration-ms:604800000}") long refreshExpirationMs) {
        if (secret == null || secret.isBlank()) {
            // Generate a random key for development; override via config in production
            this.key = Keys.secretKeyFor(SignatureAlgorithm.HS512);
            log.warn("No JWT secret configured — using generated key (NOT for production!)");
        } else {
            this.key = Keys.hmacShaKeyFor(Decoders.BASE64.decode(secret));
        }
        this.accessExpirationMs = accessExpirationMs;
        this.refreshExpirationMs = refreshExpirationMs;
    }

    public String generateAccessToken(String userId, String username, Collection<String> roles) {
        Date now = new Date();
        return Jwts.builder()
                .setSubject(userId)
                .claim("username", username)
                .claim("roles", roles)
                .claim("type", "access")
                .setIssuedAt(now)
                .setExpiration(new Date(now.getTime() + accessExpirationMs))
                .signWith(key, SignatureAlgorithm.HS512)
                .compact();
    }

    public String generateRefreshToken(String userId) {
        Date now = new Date();
        return Jwts.builder()
                .setSubject(userId)
                .claim("type", "refresh")
                .setIssuedAt(now)
                .setExpiration(new Date(now.getTime() + refreshExpirationMs))
                .signWith(key, SignatureAlgorithm.HS512)
                .compact();
    }

    public String getUserId(String token) {
        return parseClaims(token).getSubject();
    }

    public String getUsername(String token) {
        return parseClaims(token).get("username", String.class);
    }

    @SuppressWarnings("unchecked")
    public List<String> getRoles(String token) {
        return parseClaims(token).get("roles", List.class);
    }

    public boolean validateToken(String token) {
        try {
            parseClaims(token);
            return true;
        } catch (JwtException | IllegalArgumentException e) {
            log.debug("Invalid JWT: {}", e.getMessage());
            return false;
        }
    }

    public boolean isAccessToken(String token) {
        return "access".equals(parseClaims(token).get("type", String.class));
    }

    public String refreshAccessToken(String refreshToken) {
        Claims claims = parseClaims(refreshToken);
        if (!"refresh".equals(claims.get("type", String.class))) {
            throw new JwtException("Token is not a refresh token");
        }
        String userId = claims.getSubject();
        String username = claims.get("username", String.class);
        @SuppressWarnings("unchecked")
        List<String> roles = claims.get("roles", List.class);
        return generateAccessToken(userId, username, roles);
    }

    private Claims parseClaims(String token) {
        return Jwts.parserBuilder()
                .setSigningKey(key)
                .build()
                .parseClaimsJws(token)
                .getBody();
    }
}
