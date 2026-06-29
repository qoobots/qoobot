package com.qoobot.qooauth.auth.service;

import com.qoobot.qooauth.auth.entity.*;
import com.qoobot.qooauth.auth.repository.*;
import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.common.util.IdGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.*;
import java.security.cert.X509Certificate;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;

/**
 * Developer Program Service.
 *
 * Manages the QooBot Developer Program, similar to Apple Developer Program:
 * - Developer certificates (code signing identity)
 * - Skill signatures (.qooskills package integrity)
 * - Sandbox environments (isolated testing)
 * - Permission reviews (sensitive capability audit)
 */
@Service
public class DeveloperProgramService {
    private static final Logger log = LoggerFactory.getLogger(DeveloperProgramService.class);

    private final DeveloperCertificateRepository devCertRepo;
    private final SkillSignatureRepository signatureRepo;
    private final SandboxEnvironmentRepository sandboxRepo;
    private final PermissionReviewRepository reviewRepo;

    // CA key pair for developer certificate signing (in production, use HSM)
    private static KeyPair caKeyPair;
    static {
        try {
            KeyPairGenerator gen = KeyPairGenerator.getInstance("EC");
            gen.initialize(256);
            caKeyPair = gen.generateKeyPair();
        } catch (Exception e) {
            throw new RuntimeException("Failed to initialize Developer CA key pair", e);
        }
    }

    public DeveloperProgramService(DeveloperCertificateRepository devCertRepo,
                                    SkillSignatureRepository signatureRepo,
                                    SandboxEnvironmentRepository sandboxRepo,
                                    PermissionReviewRepository reviewRepo) {
        this.devCertRepo = devCertRepo;
        this.signatureRepo = signatureRepo;
        this.sandboxRepo = sandboxRepo;
        this.reviewRepo = reviewRepo;
    }

    // ============================================================
    //  Developer Certificates
    // ============================================================

    /**
     * Issue a new developer certificate.
     *
     * @param userId Developer's user ID
     * @param certType DEVELOPMENT / DISTRIBUTION / ENTERPRISE
     * @param csrPem PKCS#10 Certificate Signing Request in PEM format
     * @param teamId Optional team/organization ID
     * @param capabilities List of enabled capabilities
     */
    @Transactional
    public DeveloperCertificate issueCertificate(String userId, String certType,
                                                   String csrPem, String teamId,
                                                   List<String> capabilities) {
        // Limit active certificates per type
        List<DeveloperCertificate> existing = devCertRepo.findActiveByType(userId, certType);
        int maxCerts = "DEVELOPMENT".equals(certType) ? 5 :
                       "DISTRIBUTION".equals(certType) ? 3 : 1;
        if (existing.size() >= maxCerts) {
            throw new AuthException(ErrorCodes.SANDBOX_LIMIT_EXCEEDED,
                    "Maximum " + certType + " certificates reached: " + maxCerts);
        }

        Instant now = Instant.now();
        Instant notAfter = "DEVELOPMENT".equals(certType) ?
                now.plus(365, ChronoUnit.DAYS) :
                now.plus(1095, ChronoUnit.DAYS); // 3 years for distribution

        DeveloperCertificate cert = new DeveloperCertificate();
        cert.setCertId(IdGenerator.generateDeveloperCertId());
        cert.setUserId(userId);
        cert.setCertType(certType);
        cert.setSerialNumber(generateSerialNumber());
        cert.setSubjectDn("CN=Developer,UID=" + userId + ",OU=" + certType);
        cert.setPublicKeyPem(extractPublicKeyFromCsr(csrPem));
        cert.setCertPem(signCertificate(cert.getSubjectDn(), cert.getPublicKeyPem(), now, notAfter));
        cert.setFingerprintSha256(computeFingerprint(cert.getCertPem()));
        cert.setKeyAlgorithm("ECDSA_P256");
        cert.setNotBefore(now);
        cert.setNotAfter(notAfter);
        cert.setState("ACTIVE");
        cert.setTeamId(teamId);
        cert.setCapabilities(toJson(capabilities));
        cert.setCreatedAt(now);
        cert.setUpdatedAt(now);

        cert = devCertRepo.save(cert);
        log.info("Developer certificate {} issued for user {} type {}",
                cert.getCertId(), userId, certType);
        return cert;
    }

    /**
     * Revoke a developer certificate and invalidate all associated signatures.
     */
    @Transactional
    public void revokeCertificate(String certId, String reason) {
        devCertRepo.revokeCertificate(certId, reason);
        // Revoke all skill signatures signed with this certificate
        int revoked = signatureRepo.revokeByCertificateId(certId);
        log.warn("Developer certificate {} revoked: {}. {} skill signatures invalidated.",
                certId, reason, revoked);
    }

    /**
     * List developer's active certificates.
     */
    public List<DeveloperCertificate> getCertificates(String userId) {
        return devCertRepo.findByUserId(userId);
    }

    // ============================================================
    //  Skill Signatures
    // ============================================================

    /**
     * Sign a .qooskills skill package.
     * Verifies the developer has a valid signing certificate.
     */
    @Transactional
    public SkillSignature signSkill(String skillId, String skillVersion,
                                      String packageHash, String developerCertId,
                                      String developerUserId) {
        // Verify certificate is valid
        DeveloperCertificate cert = devCertRepo.findById(developerCertId)
                .orElseThrow(() -> new AuthException(ErrorCodes.DEVELOPER_CERT_NOT_FOUND,
                        "Developer certificate not found"));

        if (!"ACTIVE".equals(cert.getState())) {
            throw new AuthException(ErrorCodes.DEVELOPER_CERT_REVOKED,
                    "Developer certificate is not active: " + cert.getState());
        }

        if (!cert.getUserId().equals(developerUserId)) {
            throw new AuthException(ErrorCodes.DEVELOPER_NOT_VERIFIED,
                    "Certificate does not belong to this developer");
        }

        // Create ECDSA signature over package hash
        String signature = createEcdsaSignature(packageHash);

        SkillSignature sig = new SkillSignature();
        sig.setSignatureId(IdGenerator.generateSkillSignatureId());
        sig.setSkillId(skillId);
        sig.setSkillVersion(skillVersion);
        sig.setPackageHash(packageHash);
        sig.setSignature(signature);
        sig.setDeveloperCertId(developerCertId);
        sig.setDeveloperUserId(developerUserId);
        sig.setState("VALID");
        sig.setSignedAt(Instant.now());
        sig.setCreatedAt(Instant.now());

        sig = signatureRepo.save(sig);
        log.info("Skill {} v{} signed with certificate {}", skillId, skillVersion, developerCertId);
        return sig;
    }

    /**
     * Verify a skill signature.
     * Returns whether the signature is valid and the signing identity.
     */
    public SignatureVerificationResult verifySignature(String skillId, String skillVersion,
                                                        String packageHash, String signature) {
        var sigOpt = signatureRepo.findBySkillIdAndSkillVersion(skillId, skillVersion);

        if (sigOpt.isEmpty()) {
            return SignatureVerificationResult.invalid("No signature record found for this skill version");
        }

        SkillSignature sig = sigOpt.get();

        if (!"VALID".equals(sig.getState())) {
            return SignatureVerificationResult.invalid("Signature state is " + sig.getState());
        }

        // Verify hash matches
        if (!sig.getPackageHash().equals(packageHash)) {
            return SignatureVerificationResult.invalid("Package hash mismatch");
        }

        // Verify ECDSA signature
        boolean signatureValid = verifyEcdsaSignature(packageHash, signature);

        if (!signatureValid) {
            return SignatureVerificationResult.invalid("ECDSA signature verification failed");
        }

        // Verify certificate is still active
        var cert = devCertRepo.findById(sig.getDeveloperCertId());
        if (cert.isEmpty() || !"ACTIVE".equals(cert.get().getState())) {
            return SignatureVerificationResult.invalid("Signing certificate has been revoked");
        }

        return SignatureVerificationResult.valid(
                sig.getDeveloperUserId(), sig.getDeveloperCertId(),
                cert.get().getCertType(), sig.getSignedAt());
    }

    /**
     * Get signing history for a skill.
     */
    public List<SkillSignature> getSkillSignatures(String skillId) {
        return signatureRepo.findBySkillId(skillId);
    }

    // ============================================================
    //  Sandbox Environments
    // ============================================================

    /**
     * Create a sandbox environment for a developer.
     */
    @Transactional
    public SandboxEnvironment createSandbox(String userId, String name, long ttlDays) {
        // Limit active sandboxes per user
        long activeCount = sandboxRepo.countActiveByUser(userId);
        if (activeCount >= 5) {
            throw new AuthException(ErrorCodes.SANDBOX_LIMIT_EXCEEDED,
                    "Maximum 5 active sandboxes per developer");
        }

        Instant now = Instant.now();
        String defaultLimits = "{\"max_robots\":5,\"max_api_calls_per_hour\":1000," +
                "\"max_storage_mb\":500,\"allowed_scopes\":[\"read\",\"skill_test\"]}";

        SandboxEnvironment env = new SandboxEnvironment();
        env.setEnvId(IdGenerator.generateSandboxEnvId());
        env.setUserId(userId);
        env.setName(name);
        env.setState("ACTIVE");
        env.setResourceLimits(defaultLimits);
        env.setResourceUsage("{\"robot_count\":0,\"api_calls_this_hour\":0,\"storage_used_mb\":0}");
        env.setCreatedAt(now);
        env.setExpiresAt(now.plus(ttlDays, ChronoUnit.DAYS));
        env.setUpdatedAt(now);

        env = sandboxRepo.save(env);
        log.info("Sandbox {} created for user {}: {}", env.getEnvId(), userId, name);
        return env;
    }

    /**
     * List developer's sandbox environments.
     */
    public List<SandboxEnvironment> getSandboxes(String userId) {
        return sandboxRepo.findByUserId(userId);
    }

    /**
     * Terminate a sandbox environment.
     */
    @Transactional
    public void terminateSandbox(String envId, String userId) {
        SandboxEnvironment env = sandboxRepo.findByEnvIdAndUserId(envId, userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.SANDBOX_VIOLATION,
                        "Sandbox not found or not owned by user"));

        env.setState("TERMINATED");
        env.setUpdatedAt(Instant.now());
        sandboxRepo.save(env);
        log.info("Sandbox {} terminated by user {}", envId, userId);
    }

    // ============================================================
    //  Permission Reviews
    // ============================================================

    /**
     * Submit a permission review request for a skill.
     */
    @Transactional
    public PermissionReview submitReview(String skillId, String skillVersion,
                                           String developerUserId,
                                           List<String> requestedPermissions,
                                           String justification) {
        PermissionReview review = new PermissionReview();
        review.setReviewId(IdGenerator.generatePermissionReviewId());
        review.setSkillId(skillId);
        review.setSkillVersion(skillVersion);
        review.setDeveloperUserId(developerUserId);
        review.setRequestedPermissions(toJson(requestedPermissions));
        review.setJustification(justification);
        review.setState("PENDING");
        review.setSubmittedAt(Instant.now());
        review.setCreatedAt(Instant.now());
        review.setUpdatedAt(Instant.now());

        review = reviewRepo.save(review);
        log.info("Permission review {} submitted for skill {} v{}: {}",
                review.getReviewId(), skillId, skillVersion, requestedPermissions);
        return review;
    }

    /**
     * Review and decide on a permission request.
     */
    @Transactional
    public PermissionReview decideReview(String reviewId, String reviewerId,
                                           String decision, String notes,
                                           String complianceChecks) {
        PermissionReview review = reviewRepo.findById(reviewId)
                .orElseThrow(() -> new AuthException(ErrorCodes.PERMISSION_REVIEW_PENDING,
                        "Permission review not found"));

        if (!"PENDING".equals(review.getState()) && !"IN_REVIEW".equals(review.getState())) {
            throw new AuthException(ErrorCodes.PERMISSION_REVIEW_PENDING,
                    "Review is not in a reviewable state: " + review.getState());
        }

        review.setState("IN_REVIEW".equals(review.getState()) ? "APPROVED" : "IN_REVIEW");
        review.setReviewerId(reviewerId);
        review.setDecision(decision);
        review.setReviewerNotes(notes);
        review.setComplianceChecks(complianceChecks);
        review.setReviewedAt(Instant.now());
        review.setUpdatedAt(Instant.now());

        // Determine final state from decision
        if (decision != null && decision.contains("\"denied_permissions\"")) {
            // If any permissions were denied, mark as changes requested
            review.setState("CHANGES_REQUESTED");
        }

        review = reviewRepo.save(review);
        log.info("Permission review {} decided by {}: {}", reviewId, reviewerId, review.getState());
        return review;
    }

    /**
     * List pending reviews.
     */
    public List<PermissionReview> getPendingReviews() {
        return reviewRepo.findPendingReviews();
    }

    /**
     * Get review history for a skill.
     */
    public List<PermissionReview> getSkillReviewHistory(String skillId) {
        return reviewRepo.findHistoryBySkill(skillId);
    }

    // ============================================================
    //  Scheduled Tasks
    // ============================================================

    /**
     * Expire sandboxes past their TTL. Runs every hour.
     */
    @Scheduled(fixedRate = 3_600_000)
    @Transactional
    public void expireSandboxes() {
        int count = sandboxRepo.expireEnvironments(Instant.now());
        if (count > 0) {
            log.info("Expired {} sandbox environments", count);
        }
    }

    // ============================================================
    //  Helper Methods (simplified — production would use Bouncy Castle)
    // ============================================================

    private String generateSerialNumber() {
        byte[] bytes = new byte[16];
        new SecureRandom().nextBytes(bytes);
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    private String extractPublicKeyFromCsr(String csrPem) {
        // Simplified: in production, parse PKCS#10 CSR with Bouncy Castle
        return "-----BEGIN PUBLIC KEY-----\n[CSR_PUBLIC_KEY]\n-----END PUBLIC KEY-----";
    }

    private String signCertificate(String subjectDn, String publicKeyPem,
                                    Instant notBefore, Instant notAfter) {
        // Simplified: in production, create X.509 certificate with Bouncy Castle
        return "-----BEGIN CERTIFICATE-----\n[DEVELOPER_CERTIFICATE]\n-----END CERTIFICATE-----";
    }

    private String computeFingerprint(String certPem) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(certPem.getBytes());
            return Base64.getUrlEncoder().withoutPadding().encodeToString(hash);
        } catch (Exception e) {
            return "fingerprint_error";
        }
    }

    private String createEcdsaSignature(String data) {
        try {
            Signature sig = Signature.getInstance("SHA256withECDSA");
            sig.initSign(caKeyPair.getPrivate());
            sig.update(data.getBytes());
            byte[] signature = sig.sign();
            return Base64.getEncoder().encodeToString(signature);
        } catch (Exception e) {
            throw new RuntimeException("ECDSA signing failed", e);
        }
    }

    private boolean verifyEcdsaSignature(String data, String signatureB64) {
        try {
            Signature sig = Signature.getInstance("SHA256withECDSA");
            sig.initVerify(caKeyPair.getPublic());
            sig.update(data.getBytes());
            return sig.verify(Base64.getDecoder().decode(signatureB64));
        } catch (Exception e) {
            log.warn("ECDSA verification error: {}", e.getMessage());
            return false;
        }
    }

    private String toJson(List<String> list) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < list.size(); i++) {
            if (i > 0) sb.append(",");
            sb.append("\"").append(list.get(i).replace("\"", "\\\"")).append("\"");
        }
        sb.append("]");
        return sb.toString();
    }

    // ============================================================
    //  DTOs
    // ============================================================

    public static class SignatureVerificationResult {
        private final boolean valid;
        private final String reason;
        private final String developerUserId;
        private final String developerCertId;
        private final String certType;
        private final Instant signedAt;

        private SignatureVerificationResult(boolean valid, String reason,
                                             String developerUserId, String developerCertId,
                                             String certType, Instant signedAt) {
            this.valid = valid;
            this.reason = reason;
            this.developerUserId = developerUserId;
            this.developerCertId = developerCertId;
            this.certType = certType;
            this.signedAt = signedAt;
        }

        public static SignatureVerificationResult valid(String userId, String certId,
                                                         String certType, Instant signedAt) {
            return new SignatureVerificationResult(true, null, userId, certId, certType, signedAt);
        }

        public static SignatureVerificationResult invalid(String reason) {
            return new SignatureVerificationResult(false, reason, null, null, null, null);
        }

        public boolean isValid() { return valid; }
        public String getReason() { return reason; }
        public String getDeveloperUserId() { return developerUserId; }
        public String getDeveloperCertId() { return developerCertId; }
        public String getCertType() { return certType; }
        public Instant getSignedAt() { return signedAt; }
    }
}
