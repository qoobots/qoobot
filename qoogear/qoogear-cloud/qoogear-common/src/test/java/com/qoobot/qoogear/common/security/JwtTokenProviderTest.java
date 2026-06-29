package com.qoobot.qoogear.common.security;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for JwtTokenProvider.
 */
class JwtTokenProviderTest {

    private JwtTokenProvider provider;

    @BeforeEach
    void setUp() {
        provider = new JwtTokenProvider("test-secret-key-that-is-at-least-64-bytes-long-for-hs512-algorithm-testing", 900000, 604800000);
    }

    @Test
    void shouldGenerateAndValidateAccessToken() {
        String token = provider.generateAccessToken("user-001", "testuser", List.of("DEVELOPER"));
        assertNotNull(token);
        assertTrue(provider.validateToken(token));
        assertTrue(provider.isAccessToken(token));
    }

    @Test
    void shouldExtractClaims() {
        String token = provider.generateAccessToken("user-001", "testuser", List.of("DEVELOPER", "ADMIN"));
        assertEquals("user-001", provider.getUserId(token));
        assertEquals("testuser", provider.getUsername(token));
        assertEquals(List.of("DEVELOPER", "ADMIN"), provider.getRoles(token));
    }

    @Test
    void shouldGenerateAndValidateRefreshToken() {
        String token = provider.generateRefreshToken("user-001");
        assertNotNull(token);
        assertTrue(provider.validateToken(token));
        assertFalse(provider.isAccessToken(token));
    }

    @Test
    void shouldRejectInvalidToken() {
        assertFalse(provider.validateToken("invalid.token.here"));
        assertFalse(provider.validateToken(""));
        assertFalse(provider.validateToken(null));
    }

    @Test
    void shouldRejectExpiredToken() {
        JwtTokenProvider shortLived = new JwtTokenProvider(
                "test-secret-key-that-is-at-least-64-bytes-long-for-hs512-algorithm-testing",
                -1000, // already expired
                604800000);
        String token = shortLived.generateAccessToken("user-001", "testuser", List.of("DEVELOPER"));
        assertFalse(shortLived.validateToken(token));
    }

    @Test
    void shouldRefreshAccessToken() throws InterruptedException {
        String refreshToken = provider.generateRefreshToken("user-001");
        // Wait 1ms to ensure different timestamps
        Thread.sleep(1);
        String newAccessToken = provider.refreshAccessToken(refreshToken);
        assertNotNull(newAccessToken);
        assertTrue(provider.isAccessToken(newAccessToken));
    }

    @Test
    void shouldRejectRefreshWithAccessToken() {
        String accessToken = provider.generateAccessToken("user-001", "testuser", List.of("DEVELOPER"));
        assertThrows(Exception.class, () -> provider.refreshAccessToken(accessToken));
    }
}
