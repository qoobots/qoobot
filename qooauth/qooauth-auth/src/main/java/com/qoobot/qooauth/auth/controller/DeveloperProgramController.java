package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.entity.*;
import com.qoobot.qooauth.auth.service.DeveloperProgramService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST controller for QooBot Developer Program operations.
 * Manages developer certificates, skill signatures, sandboxes, and permission reviews.
 */
@RestController
@RequestMapping("/api/v1/auth/developer")
public class DeveloperProgramController {

    private final DeveloperProgramService devProgramService;

    public DeveloperProgramController(DeveloperProgramService devProgramService) {
        this.devProgramService = devProgramService;
    }

    // ---- Developer Certificates ----

    /**
     * Issue a new developer certificate.
     */
    @PostMapping("/certificates")
    public ResponseEntity<Map<String, Object>> issueCertificate(@RequestBody Map<String, Object> request) {
        String userId = (String) request.get("user_id");
        String certType = (String) request.get("cert_type");
        String csrPem = (String) request.get("csr_pem");
        String teamId = (String) request.get("team_id");

        @SuppressWarnings("unchecked")
        List<String> capabilities = (List<String>) request.getOrDefault("capabilities",
                List.of("skill_signing"));

        DeveloperCertificate cert = devProgramService.issueCertificate(
                userId, certType, csrPem, teamId, capabilities);

        return ResponseEntity.ok(Map.of(
                "cert_id", cert.getCertId(),
                "cert_type", cert.getCertType(),
                "serial_number", cert.getSerialNumber(),
                "cert_pem", cert.getCertPem(),
                "fingerprint_sha256", cert.getFingerprintSha256(),
                "not_before", cert.getNotBefore().toString(),
                "not_after", cert.getNotAfter().toString(),
                "state", cert.getState(),
                "capabilities", capabilities
        ));
    }

    /**
     * List developer's certificates.
     */
    @GetMapping("/certificates")
    public ResponseEntity<List<DeveloperCertificate>> listCertificates(@RequestParam String userId) {
        return ResponseEntity.ok(devProgramService.getCertificates(userId));
    }

    /**
     * Revoke a developer certificate.
     */
    @DeleteMapping("/certificates/{certId}")
    public ResponseEntity<Map<String, Object>> revokeCertificate(
            @PathVariable String certId,
            @RequestParam(defaultValue = "user_requested") String reason) {
        devProgramService.revokeCertificate(certId, reason);
        return ResponseEntity.ok(Map.of("status", "revoked", "reason", reason));
    }

    // ---- Skill Signatures ----

    /**
     * Sign a .qooskills package.
     */
    @PostMapping("/skills/sign")
    public ResponseEntity<Map<String, Object>> signSkill(@RequestBody Map<String, String> request) {
        String skillId = request.get("skill_id");
        String skillVersion = request.get("skill_version");
        String packageHash = request.get("package_hash");
        String developerCertId = request.get("developer_cert_id");
        String developerUserId = request.get("developer_user_id");

        SkillSignature sig = devProgramService.signSkill(
                skillId, skillVersion, packageHash, developerCertId, developerUserId);

        return ResponseEntity.ok(Map.of(
                "signature_id", sig.getSignatureId(),
                "skill_id", sig.getSkillId(),
                "skill_version", sig.getSkillVersion(),
                "package_hash", sig.getPackageHash(),
                "signature", sig.getSignature(),
                "state", sig.getState(),
                "signed_at", sig.getSignedAt().toString()
        ));
    }

    /**
     * Verify a skill signature (public endpoint — called during skill installation).
     */
    @PostMapping("/skills/verify-signature")
    public ResponseEntity<Map<String, Object>> verifySignature(@RequestBody Map<String, String> request) {
        String skillId = request.get("skill_id");
        String skillVersion = request.get("skill_version");
        String packageHash = request.get("package_hash");
        String signature = request.get("signature");

        DeveloperProgramService.SignatureVerificationResult result =
                devProgramService.verifySignature(skillId, skillVersion, packageHash, signature);

        return ResponseEntity.ok(Map.of(
                "valid", result.isValid(),
                "reason", result.getReason() != null ? result.getReason() : "",
                "developer_user_id", result.getDeveloperUserId() != null ? result.getDeveloperUserId() : "",
                "developer_cert_id", result.getDeveloperCertId() != null ? result.getDeveloperCertId() : "",
                "cert_type", result.getCertType() != null ? result.getCertType() : "",
                "signed_at", result.getSignedAt() != null ? result.getSignedAt().toString() : ""
        ));
    }

    /**
     * Get skill signing history.
     */
    @GetMapping("/skills/{skillId}/signatures")
    public ResponseEntity<List<SkillSignature>> getSignatures(@PathVariable String skillId) {
        return ResponseEntity.ok(devProgramService.getSkillSignatures(skillId));
    }

    // ---- Sandbox Environments ----

    /**
     * Create a sandbox environment.
     */
    @PostMapping("/sandboxes")
    public ResponseEntity<Map<String, Object>> createSandbox(@RequestBody Map<String, Object> request) {
        String userId = (String) request.get("user_id");
        String name = (String) request.get("name");
        long ttlDays = request.containsKey("ttl_days") ?
                ((Number) request.get("ttl_days")).longValue() : 90L;

        SandboxEnvironment env = devProgramService.createSandbox(userId, name, ttlDays);

        return ResponseEntity.ok(Map.of(
                "env_id", env.getEnvId(),
                "name", env.getName(),
                "state", env.getState(),
                "expires_at", env.getExpiresAt().toString(),
                "resource_limits", env.getResourceLimits()
        ));
    }

    /**
     * List developer's sandboxes.
     */
    @GetMapping("/sandboxes")
    public ResponseEntity<List<SandboxEnvironment>> listSandboxes(@RequestParam String userId) {
        return ResponseEntity.ok(devProgramService.getSandboxes(userId));
    }

    /**
     * Terminate a sandbox environment.
     */
    @DeleteMapping("/sandboxes/{envId}")
    public ResponseEntity<Map<String, Object>> terminateSandbox(
            @PathVariable String envId,
            @RequestParam String userId) {
        devProgramService.terminateSandbox(envId, userId);
        return ResponseEntity.ok(Map.of("status", "terminated", "env_id", envId));
    }

    // ---- Permission Reviews ----

    /**
     * Submit a permission review request.
     */
    @PostMapping("/permission-reviews")
    public ResponseEntity<Map<String, Object>> submitReview(@RequestBody Map<String, Object> request) {
        String skillId = (String) request.get("skill_id");
        String skillVersion = (String) request.get("skill_version");
        String developerUserId = (String) request.get("developer_user_id");

        @SuppressWarnings("unchecked")
        List<String> permissions = (List<String>) request.get("requested_permissions");
        String justification = (String) request.getOrDefault("justification", "");

        PermissionReview review = devProgramService.submitReview(
                skillId, skillVersion, developerUserId, permissions, justification);

        return ResponseEntity.ok(Map.of(
                "review_id", review.getReviewId(),
                "skill_id", review.getSkillId(),
                "state", review.getState(),
                "submitted_at", review.getSubmittedAt().toString()
        ));
    }

    /**
     * Decide on a permission review (admin/reviewer action).
     */
    @PostMapping("/permission-reviews/{reviewId}/decide")
    public ResponseEntity<Map<String, Object>> decideReview(
            @PathVariable String reviewId,
            @RequestBody Map<String, String> request) {
        String reviewerId = request.get("reviewer_id");
        String decision = request.get("decision");
        String notes = request.getOrDefault("notes", "");
        String complianceChecks = request.getOrDefault("compliance_checks", "{}");

        PermissionReview review = devProgramService.decideReview(
                reviewId, reviewerId, decision, notes, complianceChecks);

        return ResponseEntity.ok(Map.of(
                "review_id", review.getReviewId(),
                "state", review.getState(),
                "reviewed_at", review.getReviewedAt().toString()
        ));
    }

    /**
     * List pending reviews (admin/reviewer action).
     */
    @GetMapping("/permission-reviews/pending")
    public ResponseEntity<List<PermissionReview>> listPendingReviews() {
        return ResponseEntity.ok(devProgramService.getPendingReviews());
    }

    /**
     * Get review history for a skill.
     */
    @GetMapping("/permission-reviews/skill/{skillId}")
    public ResponseEntity<List<PermissionReview>> getSkillReviews(@PathVariable String skillId) {
        return ResponseEntity.ok(devProgramService.getSkillReviewHistory(skillId));
    }
}
