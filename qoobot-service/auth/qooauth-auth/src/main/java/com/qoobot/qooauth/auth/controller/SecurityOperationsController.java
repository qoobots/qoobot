package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.service.DdosProtectionService;
import com.qoobot.qooauth.auth.service.IntegrityVerificationService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * REST controller for security operations:
 * Integrity verification (jailbreak/root detection, binary integrity)
 * and DDoS protection (traffic analysis, WAF, blocklist management).
 */
@RestController
@RequestMapping("/api/v1/auth/security")
public class SecurityOperationsController {

    private final IntegrityVerificationService integrityService;
    private final DdosProtectionService ddosService;

    public SecurityOperationsController(IntegrityVerificationService integrityService,
                                         DdosProtectionService ddosService) {
        this.integrityService = integrityService;
        this.ddosService = ddosService;
    }

    // ---- Integrity Verification ----

    /**
     * Detect jailbreak on iOS.
     */
    @PostMapping("/integrity/jailbreak-detect")
    public ResponseEntity<Map<String, Object>> detectJailbreak(@RequestBody Map<String, Boolean> indicators) {
        IntegrityVerificationService.IntegrityResult result = integrityService.detectJailbreak(indicators);
        return ResponseEntity.ok(result.toMap());
    }

    /**
     * Detect root on Android.
     */
    @PostMapping("/integrity/root-detect")
    public ResponseEntity<Map<String, Object>> detectRoot(@RequestBody Map<String, Boolean> indicators) {
        IntegrityVerificationService.IntegrityResult result = integrityService.detectRoot(indicators);
        return ResponseEntity.ok(result.toMap());
    }

    /**
     * Detect tampering on Linux (QooBot onboard).
     */
    @PostMapping("/integrity/linux-tamper-detect")
    public ResponseEntity<Map<String, Object>> detectLinuxTampering(@RequestBody Map<String, Boolean> indicators) {
        IntegrityVerificationService.IntegrityResult result = integrityService.detectLinuxTampering(indicators);
        return ResponseEntity.ok(result.toMap());
    }

    /**
     * Verify client binary integrity.
     */
    @PostMapping("/integrity/verify-binaries")
    public ResponseEntity<Map<String, Object>> verifyBinaries(@RequestBody Map<String, Object> request) {
        @SuppressWarnings("unchecked")
        Map<String, String> clientHashes = (Map<String, String>) request.get("client_hashes");
        @SuppressWarnings("unchecked")
        Map<String, String> expectedHashes = (Map<String, String>) request.get("expected_hashes");

        IntegrityVerificationService.IntegrityResult result =
                integrityService.verifyBinaryIntegrity(clientHashes, expectedHashes);
        return ResponseEntity.ok(result.toMap());
    }

    /**
     * Verify skill package integrity.
     */
    @PostMapping("/integrity/verify-skill-package")
    public ResponseEntity<Map<String, Object>> verifySkillPackage(@RequestBody Map<String, String> request) {
        String packageHash = request.get("package_hash");
        String expectedHash = request.get("expected_hash");
        String developerSignature = request.get("developer_signature");

        IntegrityVerificationService.IntegrityResult result =
                integrityService.verifySkillPackageIntegrity(packageHash, expectedHash, developerSignature);
        return ResponseEntity.ok(result.toMap());
    }

    /**
     * Check runtime environment integrity.
     */
    @PostMapping("/integrity/runtime-environment")
    public ResponseEntity<Map<String, Object>> checkRuntime(@RequestBody Map<String, Object> envInfo) {
        IntegrityVerificationService.IntegrityResult result =
                integrityService.checkRuntimeEnvironment(envInfo);
        return ResponseEntity.ok(result.toMap());
    }

    // ---- DDoS Protection ----

    /**
     * Get traffic report.
     */
    @GetMapping("/ddos/traffic-report")
    public ResponseEntity<Map<String, Object>> getTrafficReport() {
        DdosProtectionService.TrafficReport report = ddosService.getTrafficReport();
        return ResponseEntity.ok(report.toMap());
    }

    /**
     * Get blocklist.
     */
    @GetMapping("/ddos/blocklist")
    public ResponseEntity<List<Map<String, Object>>> getBlocklist() {
        List<DdosProtectionService.BlockEntry> entries = ddosService.getBlocklist();
        List<Map<String, Object>> result = new ArrayList<>();
        for (var e : entries) {
            result.add(e.toMap());
        }
        return ResponseEntity.ok(result);
    }

    /**
     * Add IP to blocklist.
     */
    @PostMapping("/ddos/blocklist")
    public ResponseEntity<Map<String, Object>> blockIp(@RequestBody Map<String, Object> request) {
        String ip = (String) request.get("ip");
        String reason = (String) request.getOrDefault("reason", "manual_block");
        long durationMs = ((Number) request.getOrDefault("duration_ms", 600_000)).longValue();

        ddosService.addToBlocklist(ip, reason, durationMs);
        return ResponseEntity.ok(Map.of("status", "blocked", "ip", ip, "duration_ms", durationMs));
    }

    /**
     * Remove IP from blocklist.
     */
    @DeleteMapping("/ddos/blocklist/{ip}")
    public ResponseEntity<Map<String, Object>> unblockIp(@PathVariable String ip) {
        ddosService.removeFromBlocklist(ip);
        return ResponseEntity.ok(Map.of("status", "unblocked", "ip", ip));
    }

    /**
     * Check if IP is blocklisted.
     */
    @GetMapping("/ddos/blocklist/{ip}")
    public ResponseEntity<Map<String, Object>> checkBlocklisted(@PathVariable String ip) {
        boolean blocked = ddosService.isBlocklisted(ip);
        return ResponseEntity.ok(Map.of("ip", ip, "blocklisted", blocked));
    }

    /**
     * Issue a challenge for DDoS verification.
     */
    @PostMapping("/ddos/challenge")
    public ResponseEntity<Map<String, Object>> issueChallenge(@RequestBody Map<String, String> request) {
        String ip = request.get("ip");
        DdosProtectionService.Challenge challenge = ddosService.issueChallenge(ip);
        return ResponseEntity.ok(challenge.toMap());
    }

    /**
     * Verify a challenge response.
     */
    @PostMapping("/ddos/challenge/verify")
    public ResponseEntity<Map<String, Object>> verifyChallenge(@RequestBody Map<String, String> request) {
        String challengeId = request.get("challenge_id");
        String ip = request.get("ip");
        String response = request.get("response");

        boolean verified = ddosService.verifyChallenge(challengeId, ip, response);
        return ResponseEntity.ok(Map.of("verified", verified));
    }
}
