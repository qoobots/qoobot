package com.qoobot.qooauth.robot.service;

import com.qoobot.qooauth.robot.dto.CollaborationAuthRequest;
import com.qoobot.qooauth.robot.entity.CollaborationToken;
import com.qoobot.qooauth.robot.repository.CollaborationTokenRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Base64;
import java.util.Optional;
import java.util.UUID;

/**
 * HMAC-SHA256 delegation token generation and validation service.
 * Enables secure collaboration between robot devices through cryptographic tokens.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class CollaborationAuthService {

    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final int TOKEN_BYTES = 32;
    private static final String DELEGATION_SECRET = "qooauth-robot-delegation-key-v1"; // In production, use Vault/KMS

    private final CollaborationTokenRepository tokenRepository;
    private final SecureRandom secureRandom = new SecureRandom();

    /**
     * Generate a new collaboration delegation token.
     * Uses HMAC-SHA256 for token generation with a shared delegation secret.
     */
    @Transactional
    public String generateToken(CollaborationAuthRequest request) {
        byte[] tokenBytes = new byte[TOKEN_BYTES];
        secureRandom.nextBytes(tokenBytes);
        String rawToken = Base64.getUrlEncoder().withoutPadding().encodeToString(tokenBytes);

        String tokenHash = computeHmac(rawToken, request.getIssuerDeviceId() + ":" + request.getRecipientDeviceId());

        CollaborationToken token = CollaborationToken.builder()
            .tokenId(UUID.randomUUID().toString().replace("-", ""))
            .issuerDeviceId(request.getIssuerDeviceId())
            .recipientDeviceId(request.getRecipientDeviceId())
            .capabilities(request.getCapabilities())
            .tokenHash(tokenHash)
            .expiresAt(request.getExpiresAt())
            .state("ACTIVE")
            .createdAt(Instant.now())
            .build();

        tokenRepository.save(token);
        log.info("Collaboration token generated: {} (issuer={}, recipient={})",
            token.getTokenId(), request.getIssuerDeviceId(), request.getRecipientDeviceId());

        return rawToken;
    }

    /**
     * Validate a collaboration delegation token.
     * Returns the CollaborationToken entity if valid, empty otherwise.
     */
    @Transactional(readOnly = true)
    public Optional<CollaborationToken> validateToken(String rawToken, String issuerDeviceId, String recipientDeviceId) {
        String expectedHash = computeHmac(rawToken, issuerDeviceId + ":" + recipientDeviceId);

        return tokenRepository.findByIssuerDeviceId(issuerDeviceId).stream()
            .filter(t -> "ACTIVE".equals(t.getState()))
            .filter(t -> t.getExpiresAt().isAfter(Instant.now()))
            .filter(t -> expectedHash.equals(t.getTokenHash()))
            .filter(t -> t.getRecipientDeviceId().equals(recipientDeviceId))
            .findFirst();
    }

    /**
     * Revoke a specific collaboration token.
     */
    @Transactional
    public void revokeToken(String tokenId) {
        CollaborationToken token = tokenRepository.findById(tokenId)
            .orElseThrow(() -> new IllegalArgumentException("Collaboration token not found: " + tokenId));
        token.setState("REVOKED");
        tokenRepository.save(token);
        log.info("Collaboration token revoked: {}", tokenId);
    }

    /**
     * Revoke all active tokens for a device (used during trust revocation).
     */
    @Transactional
    public void revokeAllTokensForDevice(String deviceId) {
        Instant now = Instant.now();
        var activeTokens = tokenRepository.findActiveTokensForDevice(deviceId, now);
        activeTokens.forEach(t -> t.setState("REVOKED"));
        tokenRepository.saveAll(activeTokens);
        log.info("Revoked {} active collaboration tokens for device {}", activeTokens.size(), deviceId);
    }

    private String computeHmac(String data, String context) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            SecretKeySpec keySpec = new SecretKeySpec(
                DELEGATION_SECRET.getBytes(StandardCharsets.UTF_8), HMAC_ALGORITHM);
            mac.init(keySpec);
            byte[] hmacBytes = mac.doFinal((data + ":" + context).getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(hmacBytes);
        } catch (Exception e) {
            throw new RuntimeException("HMAC computation failed", e);
        }
    }
}
