package com.qoobot.qooauth.developer.controller;

import com.qoobot.qooauth.developer.dto.DeveloperCertRequest;
import com.qoobot.qooauth.developer.dto.SkillSignRequest;
import com.qoobot.qooauth.developer.entity.DeveloperCertificate;
import com.qoobot.qooauth.developer.entity.SkillSignature;
import com.qoobot.qooauth.developer.service.*;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.nio.charset.StandardCharsets;
import java.security.Principal;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/developer")
@RequiredArgsConstructor
public class DeveloperController {

    private final DeveloperCertService certService;
    private final SkillSigningService signingService;
    private final SandboxService sandboxService;
    private final PermissionReviewService permissionReviewService;

    // ---- Certificate endpoints ----

    @PostMapping("/certs")
    public ResponseEntity<DeveloperCertificate> applyForCert(
            @Valid @RequestBody DeveloperCertRequest request,
            Principal principal) {
        DeveloperCertificate cert = certService.applyForCertificate(principal.getName(), request);
        return ResponseEntity.status(HttpStatus.CREATED).body(cert);
    }

    @GetMapping("/certs")
    public ResponseEntity<List<DeveloperCertificate>> listCerts(Principal principal) {
        return ResponseEntity.ok(certService.listCertificates(principal.getName()));
    }

    @DeleteMapping("/certs/{certId}")
    public ResponseEntity<Map<String, String>> revokeCert(
            @PathVariable String certId,
            Principal principal) {
        certService.revokeCertificate(certId, principal.getName());
        return ResponseEntity.ok(Map.of("status", "revoked", "cert_id", certId));
    }

    // ---- Skill signing endpoints ----

    @PostMapping("/sign")
    public ResponseEntity<SkillSignature> signSkill(
            @Valid @RequestBody SkillSignRequest request,
            Principal principal) {
        // In production, skill data and private key would be transmitted securely
        byte[] skillData = request.getSkillHash().getBytes(StandardCharsets.UTF_8);
        byte[] privateKeyBytes = new byte[0]; // Would come from secure key storage

        SkillSignature signature = signingService.signSkill(
            principal.getName(), request.getSkillHash(), skillData, privateKeyBytes);
        return ResponseEntity.status(HttpStatus.CREATED).body(signature);
    }

    @GetMapping("/sign/verify/{skillHash}")
    public ResponseEntity<SkillSigningService.VerificationResult> verifySkill(
            @PathVariable String skillHash) {
        byte[] skillData = skillHash.getBytes(StandardCharsets.UTF_8);
        byte[] publicKeyBytes = new byte[0]; // Would come from certificate store

        SkillSigningService.VerificationResult result = signingService.verifySkill(skillHash, skillData, publicKeyBytes);
        return ResponseEntity.ok(result);
    }

    // ---- Sandbox endpoints ----

    @GetMapping("/sandbox")
    public ResponseEntity<SandboxService.SandboxStatus> sandboxStatus(Principal principal) {
        return ResponseEntity.ok(sandboxService.getSandboxStatus(principal.getName()));
    }

    @PostMapping("/sandbox")
    public ResponseEntity<SandboxService.Sandbox> createSandbox(
            @RequestBody Map<String, Long> request,
            Principal principal) {
        long ttl = request.getOrDefault("ttl_seconds", 3600L);
        SandboxService.Sandbox sandbox = sandboxService.createSandbox(principal.getName(), ttl);
        return ResponseEntity.status(HttpStatus.CREATED).body(sandbox);
    }

    @DeleteMapping("/sandbox/{sandboxId}")
    public ResponseEntity<Map<String, String>> destroySandbox(
            @PathVariable String sandboxId,
            Principal principal) {
        sandboxService.destroySandbox(sandboxId, principal.getName());
        return ResponseEntity.ok(Map.of("status", "destroyed", "sandbox_id", sandboxId));
    }

    // ---- Permission review endpoints ----

    @PostMapping("/permissions/review")
    public ResponseEntity<PermissionReviewService.PermissionRequest> submitReview(
            @RequestBody Map<String, Object> request,
            Principal principal) {
        @SuppressWarnings("unchecked")
        List<String> permissions = (List<String>) request.get("permissions");
        String justification = (String) request.getOrDefault("justification", "");

        PermissionReviewService.PermissionRequest pr = permissionReviewService.submitRequest(
            principal.getName(), permissions, justification);
        return ResponseEntity.status(HttpStatus.CREATED).body(pr);
    }

    @GetMapping("/permissions")
    public ResponseEntity<List<PermissionReviewService.PermissionRequest>> listPermissions(Principal principal) {
        return ResponseEntity.ok(permissionReviewService.listDeveloperRequests(principal.getName()));
    }

    @GetMapping("/permissions/pending")
    public ResponseEntity<List<PermissionReviewService.PermissionRequest>> listPending() {
        return ResponseEntity.ok(permissionReviewService.listPendingRequests());
    }

    @PutMapping("/permissions/{requestId}")
    public ResponseEntity<PermissionReviewService.PermissionRequest> reviewPermission(
            @PathVariable String requestId,
            @RequestBody Map<String, Object> review,
            Principal principal) {
        boolean approved = (boolean) review.getOrDefault("approved", false);
        String comment = (String) review.getOrDefault("comment", "");

        PermissionReviewService.PermissionRequest result = permissionReviewService.reviewRequest(
            requestId, principal.getName(), approved, comment);
        return ResponseEntity.ok(result);
    }
}
