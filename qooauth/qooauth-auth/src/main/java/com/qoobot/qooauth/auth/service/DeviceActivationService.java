package com.qoobot.qooauth.auth.service;

import com.qoobot.qooauth.auth.entity.ActivationChallenge;
import com.qoobot.qooauth.auth.entity.DeviceActivation;
import com.qoobot.qooauth.auth.entity.DeviceCertificate;
import com.qoobot.qooauth.auth.repository.ActivationChallengeRepository;
import com.qoobot.qooauth.auth.repository.DeviceActivationRepository;
import com.qoobot.qooauth.auth.repository.DeviceCertificateRepository;
import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.common.util.IdGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.spec.X509EncodedKeySpec;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Base64;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Device Activation Service.
 *
 * Manages the first-boot device activation lifecycle:
 * 1. Device presents bootstrap certificate → server creates activation session
 * 2. Server issues cryptographic challenge → device proves possession of bootstrap key
 * 3. Challenge verified → server issues operational certificate → binds device to user account
 * 4. Activation expires after configurable window (default 7 days)
 *
 * Mirrors Apple Device Enrollment / Google Zero-Touch Enrollment.
 */
@Service
public class DeviceActivationService {

    private static final Logger log = LoggerFactory.getLogger(DeviceActivationService.class);
    private static final int DEFAULT_ACTIVATION_WINDOW_DAYS = 7;
    private static final int CHALLENGE_VALIDITY_MINUTES = 10;
    private static final int MAX_ACTIVATIONS_PER_DEVICE = 3;
    private static final String ACTIVATION_TOKEN_AES_ALGORITHM = "AES/GCM/NoPadding";
    private static final int GCM_IV_LENGTH = 12;
    private static final int GCM_TAG_LENGTH = 128;

    private final DeviceActivationRepository activationRepo;
    private final ActivationChallengeRepository challengeRepo;
    private final DeviceCertificateRepository certRepo;
    private final DeviceCertificateService certService;
    private final SecretKey activationTokenKey; // AES-256 key for activation token encryption

    public DeviceActivationService(DeviceActivationRepository activationRepo,
                                   ActivationChallengeRepository challengeRepo,
                                   DeviceCertificateRepository certRepo,
                                   DeviceCertificateService certService) {
        this.activationRepo = activationRepo;
        this.challengeRepo = challengeRepo;
        this.certRepo = certRepo;
        this.certService = certService;

        // Derive AES-256 key from environment or generate one for this runtime
        byte[] keyBytes = new byte[32];
        // In production, this would come from KMS / HSM
        new SecureRandom().nextBytes(keyBytes);
        this.activationTokenKey = new SecretKeySpec(keyBytes, "AES");
    }

    // ========================================================================
    // Activation Initiation
    // ========================================================================

    /**
     * Step 1: Device initiates activation by presenting its bootstrap certificate.
     * The bootstrap certificate was issued during manufacturing (see issueBootstrapCertificate).
     * Server creates an activation session and returns an encrypted activation token.
     */
    @Transactional
    public ActivationInitiateResponse initiateActivation(String userId, String bootstrapCertId,
                                                          String deviceSerial, String deviceModel,
                                                          String firmwareVersion, String hardwareFingerprint) {
        // Validate bootstrap certificate exists and is in ACTIVE state
        DeviceCertificate bootstrapCert = certRepo.findById(bootstrapCertId)
                .orElseThrow(() -> new AuthException(ErrorCodes.DEVICE_CERT_NOT_FOUND,
                        "Bootstrap certificate not found: " + bootstrapCertId));

        if (!"ACTIVE".equals(bootstrapCert.getState())) {
            throw new AuthException(ErrorCodes.DEVICE_CERT_STATE_INVALID,
                    "Bootstrap certificate is not in ACTIVE state: " + bootstrapCert.getState());
        }

        // Check if bootstrap cert is expired
        if (bootstrapCert.getNotAfter().isBefore(Instant.now())) {
            throw new AuthException(ErrorCodes.DEVICE_CERT_EXPIRED,
                    "Bootstrap certificate has expired");
        }

        // Check if device serial already has an active activation
        Optional<DeviceActivation> existing = activationRepo
                .findByDeviceSerialAndActivationState(deviceSerial, "ACTIVATED");
        if (existing.isPresent()) {
            throw new AuthException(ErrorCodes.DEVICE_ALREADY_BOUND,
                    "Device serial " + deviceSerial + " is already activated");
        }

        // Count pending/active activations for this device serial
        boolean hasPending = activationRepo.existsByDeviceSerialAndActivationStateIn(
                deviceSerial, List.of("PENDING", "CHALLENGED"));
        if (hasPending) {
            throw new AuthException(ErrorCodes.DEVICE_ACTIVATION_IN_PROGRESS,
                    "An activation is already in progress for device serial: " + deviceSerial);
        }

        String deviceId = IdGenerator.generateDeviceId();
        String activationId = IdGenerator.generateActivationId();
        Instant now = Instant.now();
        Instant expiresAt = now.plus(DEFAULT_ACTIVATION_WINDOW_DAYS, ChronoUnit.DAYS);

        // Generate encrypted activation token
        String activationToken = encryptActivationToken(activationId, deviceId, deviceSerial);

        DeviceActivation activation = new DeviceActivation();
        activation.setActivationId(activationId);
        activation.setUserId(userId);
        activation.setDeviceId(deviceId);
        activation.setBootstrapCertId(bootstrapCertId);
        activation.setDeviceSerial(deviceSerial);
        activation.setDeviceModel(deviceModel);
        activation.setFirmwareVersion(firmwareVersion);
        activation.setHardwareFingerprint(hardwareFingerprint);
        activation.setActivationState("PENDING");
        activation.setActivationToken(activationToken);
        activation.setExpiresAt(expiresAt);
        activation.setMaxChallengeAttempts(5);
        activation.setCreatedAt(now);
        activation.setUpdatedAt(now);

        activationRepo.save(activation);

        log.info("Device activation initiated: activationId={}, userId={}, serial={}",
                activationId, userId, deviceSerial);

        return new ActivationInitiateResponse(
                activationId, deviceId, activationToken, expiresAt.toString());
    }

    /**
     * Step 2: Server issues a cryptographic challenge to the device.
     * Device must sign the nonce with its bootstrap private key to prove possession.
     */
    @Transactional
    public ActivationChallengeResponse issueChallenge(String activationId) {
        DeviceActivation activation = activationRepo.findById(activationId)
                .orElseThrow(() -> new AuthException(ErrorCodes.DEVICE_ACTIVATION_NOT_FOUND,
                        "Activation not found: " + activationId));

        if (!"PENDING".equals(activation.getActivationState())
                && !"CHALLENGED".equals(activation.getActivationState())) {
            throw new AuthException(ErrorCodes.DEVICE_ACTIVATION_STATE_INVALID,
                    "Activation is not in a challengeable state: " + activation.getActivationState());
        }

        // Check activation expiry
        if (activation.getExpiresAt() != null && activation.getExpiresAt().isBefore(Instant.now())) {
            activation.setActivationState("EXPIRED");
            activation.setUpdatedAt(Instant.now());
            activationRepo.save(activation);
            throw new AuthException(ErrorCodes.DEVICE_ACTIVATION_EXPIRED,
                    "Activation session has expired");
        }

        // Check max challenge attempts
        if (activation.getChallengeAttempts() >= activation.getMaxChallengeAttempts()) {
            activation.setActivationState("FAILED");
            activation.setFailureReason("Max challenge attempts exceeded");
            activation.setUpdatedAt(Instant.now());
            activationRepo.save(activation);
            throw new AuthException(ErrorCodes.DEVICE_ACTIVATION_MAX_ATTEMPTS,
                    "Max challenge attempts (" + activation.getMaxChallengeAttempts() + ") exceeded");
        }

        Instant now = Instant.now();
        Instant challengeExpires = now.plus(CHALLENGE_VALIDITY_MINUTES, ChronoUnit.MINUTES);

        // Generate fresh challenge nonce (48 bytes random → base64)
        byte[] nonceBytes = new byte[48];
        new SecureRandom().nextBytes(nonceBytes);
        String challengeNonce = Base64.getUrlEncoder().withoutPadding().encodeToString(nonceBytes);

        // Create challenge record
        String challengeId = IdGenerator.generateActivationChallengeId();
        ActivationChallenge challenge = new ActivationChallenge();
        challenge.setChallengeId(challengeId);
        challenge.setActivationId(activationId);
        challenge.setDeviceId(activation.getDeviceId());
        challenge.setChallengeType("SIGNATURE");
        challenge.setChallengeNonce(challengeNonce);
        challenge.setChallengeState("PENDING");
        challenge.setIssuedAt(now);
        challenge.setExpiresAt(challengeExpires);

        challengeRepo.save(challenge);

        // Update activation
        activation.setActivationState("CHALLENGED");
        activation.setChallengeNonce(challengeNonce);
        activation.setChallengeIssuedAt(now);
        activation.setChallengeExpiresAt(challengeExpires);
        activation.setUpdatedAt(now);
        activationRepo.incrementChallengeAttempts(activationId, now);

        log.info("Challenge issued: activationId={}, challengeId={}, type=SIGNATURE",
                activationId, challengeId);

        return new ActivationChallengeResponse(challengeId, challengeNonce,
                "ECDSA_P256_SHA256", challengeExpires.toString());
    }

    /**
     * Step 3: Device submits signed challenge response.
     * Server verifies the signature against the bootstrap certificate's public key.
     */
    @Transactional
    public ActivationVerifyResponse verifyChallenge(String activationId, String challengeId,
                                                     String signedNonceBase64) {
        DeviceActivation activation = activationRepo.findById(activationId)
                .orElseThrow(() -> new AuthException(ErrorCodes.DEVICE_ACTIVATION_NOT_FOUND,
                        "Activation not found: " + activationId));

        if (!"CHALLENGED".equals(activation.getActivationState())) {
            throw new AuthException(ErrorCodes.DEVICE_ACTIVATION_STATE_INVALID,
                    "Activation is not in CHALLENGED state: " + activation.getActivationState());
        }

        ActivationChallenge challenge = challengeRepo.findById(challengeId)
                .orElseThrow(() -> new AuthException(ErrorCodes.DEVICE_CHALLENGE_NOT_FOUND,
                        "Challenge not found: " + challengeId));

        if (!"PENDING".equals(challenge.getChallengeState())) {
            throw new AuthException(ErrorCodes.DEVICE_CHALLENGE_STATE_INVALID,
                    "Challenge is not in PENDING state: " + challenge.getChallengeState());
        }

        if (challenge.getExpiresAt().isBefore(Instant.now())) {
            challenge.setChallengeState("EXPIRED");
            challengeRepo.save(challenge);
            throw new AuthException(ErrorCodes.DEVICE_CHALLENGE_EXPIRED,
                    "Challenge has expired");
        }

        // Verify signature using bootstrap certificate's public key
        boolean signatureValid;
        try {
            DeviceCertificate bootstrapCert = certRepo.findById(activation.getBootstrapCertId())
                    .orElseThrow(() -> new AuthException(ErrorCodes.DEVICE_CERT_NOT_FOUND,
                            "Bootstrap certificate not found"));

            // Parse public key from PEM
            String publicKeyPem = bootstrapCert.getPublicKeyPem()
                    .replace("-----BEGIN PUBLIC KEY-----", "")
                    .replace("-----END PUBLIC KEY-----", "")
                    .replaceAll("\\s", "");
            byte[] publicKeyBytes = Base64.getDecoder().decode(publicKeyPem);
            X509EncodedKeySpec keySpec = new X509EncodedKeySpec(publicKeyBytes);
            KeyFactory keyFactory = KeyFactory.getInstance("EC");
            PublicKey publicKey = keyFactory.generatePublic(keySpec);

            // Verify signature
            Signature signature = Signature.getInstance("SHA256withECDSA");
            signature.initVerify(publicKey);
            signature.update(challenge.getChallengeNonce().getBytes(StandardCharsets.UTF_8));
            byte[] signedBytes = Base64.getDecoder().decode(signedNonceBase64);
            signatureValid = signature.verify(signedBytes);

        } catch (Exception e) {
            log.warn("Signature verification error: activationId={}", activationId, e);
            signatureValid = false;
        }

        Instant now = Instant.now();
        challenge.setActualResponse(signedNonceBase64);
        challenge.setResponseValid(signatureValid);
        challenge.setRespondedAt(now);

        if (signatureValid) {
            challenge.setChallengeState("ACCEPTED");
            activation.setActivationState("ACTIVATED");
            activation.setActivatedAt(now);
            activation.setUpdatedAt(now);

            // Issue operational certificate to replace the bootstrap cert
            try {
                DeviceCertificate bootstrapCert = certRepo.findById(activation.getBootstrapCertId())
                        .orElse(null);
                if (bootstrapCert != null) {
                    // Build CSR from bootstrap key (in production, device sends CSR)
                    // Here we issue directly using the known device public key
                    String deviceDn = "CN=device-" + activation.getDeviceId() + ",O=QooBot";
                    DeviceCertificateService.IssuedCertificate issuedCert =
                            certService.issueCertificateFromPublicKey(
                                    activation.getDeviceId(), activation.getUserId(),
                                    bootstrapCert.getPublicKeyPem(), deviceDn,
                                    bootstrapCert.getKeyAlgorithm(), null);

                    activation.setCertId(issuedCert.certId());

                    // Revoke bootstrap cert (it was only for activation)
                    certService.revokeCertificate(activation.getBootstrapCertId(),
                            "superseded", Instant.now());
                }
            } catch (Exception e) {
                log.error("Failed to issue operational certificate during activation: activationId={}",
                        activationId, e);
                // Activation is still valid even if cert issuance fails — device can re-request
            }

            log.info("Device activation verified and completed: activationId={}, deviceId={}, userId={}",
                    activationId, activation.getDeviceId(), activation.getUserId());
        } else {
            challenge.setChallengeState("REJECTED");
            activation.setFailureReason("Signature verification failed");
            // If max attempts reached, fail the activation
            if (activation.getChallengeAttempts() >= activation.getMaxChallengeAttempts()) {
                activation.setActivationState("FAILED");
            } else {
                activation.setActivationState("PENDING"); // Allow retry
            }
            activation.setUpdatedAt(now);

            log.warn("Challenge verification failed: activationId={}, challengeId={}",
                    activationId, challengeId);
        }

        challengeRepo.save(challenge);
        activationRepo.save(activation);

        return new ActivationVerifyResponse(
                signatureValid, activation.getActivationState(),
                activation.getCertId(), activation.getDeviceId());
    }

    // ========================================================================
    // Query APIs
    // ========================================================================

    @Transactional(readOnly = true)
    public DeviceActivation getActivation(String activationId) {
        return activationRepo.findById(activationId)
                .orElseThrow(() -> new AuthException(ErrorCodes.DEVICE_ACTIVATION_NOT_FOUND,
                        "Activation not found: " + activationId));
    }

    @Transactional(readOnly = true)
    public DeviceActivation getActivationByDevice(String deviceId) {
        return activationRepo.findByDeviceId(deviceId)
                .orElseThrow(() -> new AuthException(ErrorCodes.DEVICE_ACTIVATION_NOT_FOUND,
                        "Activation not found for device: " + deviceId));
    }

    @Transactional(readOnly = true)
    public List<DeviceActivation> listActivationsByUser(String userId) {
        return activationRepo.findByUserId(userId);
    }

    @Transactional(readOnly = true)
    public List<ActivationChallenge> listChallenges(String activationId) {
        return challengeRepo.findByActivationId(activationId);
    }

    /**
     * Revoke a device activation — unbinds the device from the user account.
     */
    @Transactional
    public void revokeActivation(String activationId, String reason) {
        DeviceActivation activation = activationRepo.findById(activationId)
                .orElseThrow(() -> new AuthException(ErrorCodes.DEVICE_ACTIVATION_NOT_FOUND,
                        "Activation not found: " + activationId));

        if ("REVOKED".equals(activation.getActivationState())) {
            throw new AuthException(ErrorCodes.DEVICE_ACTIVATION_ALREADY_REVOKED,
                    "Activation is already revoked");
        }

        Instant now = Instant.now();
        activation.setActivationState("REVOKED");
        activation.setFailureReason(reason);
        activation.setUpdatedAt(now);
        activationRepo.save(activation);

        // Also revoke the associated operational certificate if any
        if (activation.getCertId() != null) {
            try {
                certService.revokeCertificate(activation.getCertId(),
                        "privilegeWithdrawn", Instant.now());
            } catch (Exception e) {
                log.warn("Failed to revoke operational cert during activation revocation: certId={}",
                        activation.getCertId(), e);
            }
        }

        log.info("Device activation revoked: activationId={}, reason={}", activationId, reason);
    }

    // ========================================================================
    // Scheduled Tasks
    // ========================================================================

    /**
     * Expire pending/challenged activations past their expiry window.
     * Runs every hour.
     */
    @Scheduled(fixedRate = 3600000)
    @Transactional
    public void expireStaleActivations() {
        Instant now = Instant.now();
        int expired = activationRepo.expirePendingActivations(now);
        if (expired > 0) {
            log.info("Expired {} stale device activations", expired);
        }
    }

    /**
     * Expire pending challenges past their validity window.
     * Runs every 5 minutes.
     */
    @Scheduled(fixedRate = 300000)
    @Transactional
    public void expireStaleChallenges() {
        int expired = challengeRepo.expirePendingChallenges(Instant.now());
        if (expired > 0) {
            log.info("Expired {} stale activation challenges", expired);
        }
    }

    // ========================================================================
    // Private Helpers
    // ========================================================================

    /**
     * Encrypt activation token with AES-256-GCM.
     * The encrypted token is returned as base64 and can only be decrypted by the server.
     */
    private String encryptActivationToken(String activationId, String deviceId, String deviceSerial) {
        try {
            Cipher cipher = Cipher.getInstance(ACTIVATION_TOKEN_AES_ALGORITHM);
            byte[] iv = new byte[GCM_IV_LENGTH];
            new SecureRandom().nextBytes(iv);
            GCMParameterSpec spec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);

            cipher.init(Cipher.ENCRYPT_MODE, activationTokenKey, spec);

            String plaintext = activationId + ":" + deviceId + ":" + deviceSerial + ":"
                    + UUID.randomUUID();
            byte[] ciphertext = cipher.doFinal(plaintext.getBytes(StandardCharsets.UTF_8));

            // Prepend IV to ciphertext
            byte[] combined = new byte[iv.length + ciphertext.length];
            System.arraycopy(iv, 0, combined, 0, iv.length);
            System.arraycopy(ciphertext, 0, combined, iv.length, ciphertext.length);

            return Base64.getUrlEncoder().withoutPadding().encodeToString(combined);
        } catch (Exception e) {
            throw new RuntimeException("Failed to encrypt activation token", e);
        }
    }

    // ========================================================================
    // Response DTOs
    // ========================================================================

    public record ActivationInitiateResponse(String activationId, String deviceId,
                                              String activationToken, String expiresAt) {}

    public record ActivationChallengeResponse(String challengeId, String challengeNonce,
                                               String algorithm, String expiresAt) {}

    public record ActivationVerifyResponse(boolean verified, String state,
                                            String certId, String deviceId) {}
}
