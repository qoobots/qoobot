package com.qoobot.qooauth.developer.service;

import com.qoobot.qooauth.developer.dto.DeveloperCertRequest;
import com.qoobot.qooauth.developer.entity.DeveloperCertificate;
import com.qoobot.qooauth.developer.repository.DeveloperCertRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.spec.ECGenParameterSpec;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Base64;
import java.util.List;
import java.util.UUID;

/**
 * 3-tier developer certificate lifecycle management.
 * DEV: Development certificates (30-day expiry)
 * DIST: Distribution certificates (1-year expiry)
 * ENTERPRISE: Enterprise certificates (2-year expiry)
 *
 * Uses ECDSA (P-256) for certificate signing.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DeveloperCertService {

    private static final int DEV_CERT_TTL_DAYS = 30;
    private static final int DIST_CERT_TTL_DAYS = 365;
    private static final int ENTERPRISE_CERT_TTL_DAYS = 730;
    private static final int MAX_CERTS_PER_TYPE = 5;

    private final DeveloperCertRepository certRepository;

    @Transactional
    public DeveloperCertificate applyForCertificate(String userId, DeveloperCertRequest request) {
        // Validate cert type
        CertType certType = CertType.fromString(request.getCertType());

        // Check quota
        long existingCerts = certRepository.countByUserIdAndCertTypeAndState(userId, certType.name(), "ACTIVE");
        if (existingCerts >= MAX_CERTS_PER_TYPE) {
            throw new IllegalStateException(
                "Maximum active " + certType + " certificates (" + MAX_CERTS_PER_TYPE + ") reached");
        }

        // Generate ECDSA key pair
        KeyPair keyPair = generateEcdsaKeyPair();

        // Create certificate
        String serialNumber = generateSerialNumber();
        String fingerprint = computeSha256Fingerprint(keyPair.getPublic().getEncoded());

        Instant expiresAt = Instant.now().plus(certType.getTtlDays(), ChronoUnit.DAYS);

        DeveloperCertificate cert = DeveloperCertificate.builder()
            .certId(UUID.randomUUID().toString().replace("-", ""))
            .userId(userId)
            .certType(certType.name())
            .teamId(request.getTeamId())
            .serialNumber(serialNumber)
            .sha256Fingerprint(fingerprint)
            .expiresAt(expiresAt)
            .state("ACTIVE")
            .capabilities(certType.getDefaultCapabilities())
            .createdAt(Instant.now())
            .build();

        DeveloperCertificate saved = certRepository.save(cert);
        log.info("{} certificate issued to user {} (serial: {})", certType, userId, serialNumber);
        return saved;
    }

    @Transactional(readOnly = true)
    public List<DeveloperCertificate> listCertificates(String userId) {
        return certRepository.findByUserId(userId);
    }

    @Transactional(readOnly = true)
    public List<DeveloperCertificate> listActiveCertificates(String userId) {
        return certRepository.findByUserIdAndState(userId, "ACTIVE");
    }

    @Transactional
    public void revokeCertificate(String certId, String userId) {
        DeveloperCertificate cert = certRepository.findById(certId)
            .orElseThrow(() -> new IllegalArgumentException("Certificate not found: " + certId));

        if (!cert.getUserId().equals(userId)) {
            throw new SecurityException("Certificate does not belong to user: " + userId);
        }

        cert.setState("REVOKED");
        cert.setRevokedAt(Instant.now());
        certRepository.save(cert);
        log.info("Certificate {} revoked for user {}", certId, userId);
    }

    /**
     * Generate an ECDSA P-256 key pair for certificate signing.
     */
    private KeyPair generateEcdsaKeyPair() {
        try {
            KeyPairGenerator keyGen = KeyPairGenerator.getInstance("EC");
            ECGenParameterSpec ecSpec = new ECGenParameterSpec("secp256r1");
            keyGen.initialize(ecSpec, new SecureRandom());
            return keyGen.generateKeyPair();
        } catch (Exception e) {
            throw new RuntimeException("Failed to generate ECDSA key pair", e);
        }
    }

    /**
     * Sign data using ECDSA with the developer's private key.
     */
    public String signData(byte[] data, byte[] privateKeyBytes) {
        try {
            KeyFactory keyFactory = KeyFactory.getInstance("EC");
            PKCS8EncodedKeySpec keySpec = new PKCS8EncodedKeySpec(privateKeyBytes);
            PrivateKey privateKey = keyFactory.generatePrivate(keySpec);

            Signature ecdsaSign = Signature.getInstance("SHA256withECDSA");
            ecdsaSign.initSign(privateKey);
            ecdsaSign.update(data);
            byte[] signature = ecdsaSign.sign();
            return Base64.getEncoder().encodeToString(signature);
        } catch (Exception e) {
            throw new RuntimeException("ECDSA signing failed", e);
        }
    }

    /**
     * Verify an ECDSA signature against public key bytes.
     */
    public boolean verifySignature(byte[] data, String signatureB64, byte[] publicKeyBytes) {
        try {
            KeyFactory keyFactory = KeyFactory.getInstance("EC");
            X509EncodedKeySpec keySpec = new X509EncodedKeySpec(publicKeyBytes);
            PublicKey publicKey = keyFactory.generatePublic(keySpec);

            Signature ecdsaVerify = Signature.getInstance("SHA256withECDSA");
            ecdsaVerify.initVerify(publicKey);
            ecdsaVerify.update(data);
            return ecdsaVerify.verify(Base64.getDecoder().decode(signatureB64));
        } catch (Exception e) {
            log.error("ECDSA signature verification failed", e);
            return false;
        }
    }

    private String generateSerialNumber() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 16).toUpperCase();
    }

    private String computeSha256Fingerprint(byte[] data) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(data);
            StringBuilder hex = new StringBuilder();
            for (byte b : hash) {
                hex.append(String.format("%02x", b));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }

    enum CertType {
        DEV(DEV_CERT_TTL_DAYS, List.of("debug", "install", "run")),
        DIST(DIST_CERT_TTL_DAYS, List.of("distribute", "sign", "publish")),
        ENTERPRISE(ENTERPRISE_CERT_TTL_DAYS, List.of("debug", "install", "run", "distribute", "sign", "publish", "enterprise"));

        private final int ttlDays;
        private final List<String> defaultCapabilities;

        CertType(int ttlDays, List<String> defaultCapabilities) {
            this.ttlDays = ttlDays;
            this.defaultCapabilities = defaultCapabilities;
        }

        public int getTtlDays() { return ttlDays; }
        public List<String> getDefaultCapabilities() { return defaultCapabilities; }

        static CertType fromString(String type) {
            try {
                return CertType.valueOf(type.toUpperCase());
            } catch (IllegalArgumentException e) {
                throw new IllegalArgumentException("Invalid certificate type: " + type + ". Must be DEV, DIST, or ENTERPRISE.");
            }
        }
    }
}
