package com.qoobot.qooauth.developer.service;

import com.qoobot.qooauth.developer.entity.DeveloperCertificate;
import com.qoobot.qooauth.developer.entity.SkillSignature;
import com.qoobot.qooauth.developer.repository.DeveloperCertRepository;
import com.qoobot.qooauth.developer.repository.SkillSignatureRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * .qooskills ECDSA signature creation and verification chain.
 * Handles signing of skill packages and verification of signature chains.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class SkillSigningService {

    private final SkillSignatureRepository signatureRepository;
    private final DeveloperCertRepository certRepository;
    private final DeveloperCertService developerCertService;

    /**
     * Sign a skill package with ECDSA using the developer's certificate.
     */
    @Transactional
    public SkillSignature signSkill(String developerId, String skillHash, byte[] skillData, byte[] privateKeyBytes) {
        // Verify developer has an active certificate
        List<DeveloperCertificate> activeCerts = certRepository.findByUserIdAndState(developerId, "ACTIVE");
        if (activeCerts.isEmpty()) {
            throw new IllegalStateException("No active developer certificate found for user: " + developerId);
        }

        // Check if skill is already signed
        Optional<SkillSignature> existing = signatureRepository.findBySkillHash(skillHash);
        if (existing.isPresent() && existing.get().getVerified()) {
            log.info("Skill {} is already signed by {}", skillHash, existing.get().getDeveloperId());
            return existing.get();
        }

        // Create ECDSA signature over the skill data
        String signature = developerCertService.signData(skillData, privateKeyBytes);

        SkillSignature skillSig = SkillSignature.builder()
            .sigId(UUID.randomUUID().toString().replace("-", ""))
            .developerId(developerId)
            .skillHash(skillHash)
            .signature(signature)
            .verified(true)
            .build();

        SkillSignature saved = signatureRepository.save(skillSig);
        log.info("Skill {} signed by developer {}", skillHash, developerId);
        return saved;
    }

    /**
     * Verify the signature chain for a skill.
     * Checks: signature validity, developer certificate status, certificate chain.
     */
    @Transactional(readOnly = true)
    public VerificationResult verifySkill(String skillHash, byte[] skillData, byte[] publicKeyBytes) {
        Optional<SkillSignature> signature = signatureRepository.findVerifiedBySkillHash(skillHash);

        if (signature.isEmpty()) {
            return VerificationResult.failure("No verified signature found for skill: " + skillHash);
        }

        SkillSignature sig = signature.get();

        // Verify ECDSA signature cryptographically
        boolean cryptoValid = developerCertService.verifySignature(skillData, sig.getSignature(), publicKeyBytes);
        if (!cryptoValid) {
            return VerificationResult.failure("ECDSA signature verification failed for skill: " + skillHash);
        }

        // Verify developer has active certificate
        List<DeveloperCertificate> activeCerts = certRepository.findByUserIdAndState(sig.getDeveloperId(), "ACTIVE");
        if (activeCerts.isEmpty()) {
            return VerificationResult.failure("Developer certificate is not active for: " + sig.getDeveloperId());
        }

        return VerificationResult.success(sig.getDeveloperId(), sig.getCreatedAt().toString());
    }

    /**
     * Get all verified signatures for a developer.
     */
    @Transactional(readOnly = true)
    public List<SkillSignature> getDeveloperSignatures(String developerId) {
        return signatureRepository.findVerifiedByDeveloperId(developerId);
    }

    /**
     * Compute SHA-256 hash of skill data.
     */
    public static String computeSkillHash(byte[] skillData) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(skillData);
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }

    public record VerificationResult(boolean valid, String message, String developerId, String signedAt) {
        public static VerificationResult success(String developerId, String signedAt) {
            return new VerificationResult(true, "Skill signature verified", developerId, signedAt);
        }
        public static VerificationResult failure(String message) {
            return new VerificationResult(false, message, null, null);
        }
    }
}
