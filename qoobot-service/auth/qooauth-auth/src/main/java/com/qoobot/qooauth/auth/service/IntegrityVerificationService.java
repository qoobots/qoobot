package com.qoobot.qooauth.auth.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.security.MessageDigest;
import java.util.*;

/**
 * Integrity Verification Service.
 *
 * Verifies client integrity before granting access:
 * - Jailbreak/Root detection for mobile devices
 * - Client binary integrity attestation
 * - Runtime environment validation
 * - Tamper detection for .qooskills packages
 */
@Service
public class IntegrityVerificationService {
    private static final Logger log = LoggerFactory.getLogger(IntegrityVerificationService.class);

    /**
     * Known integrity violations and their risk levels.
     */
    public enum IntegrityRisk {
        CLEAN,       // No issues detected
        LOW,         // Minor anomalies (e.g., debug mode)
        MEDIUM,      // Suspicious indicators (e.g., unofficial app store)
        HIGH,        // Strong evidence of tampering (e.g., root/jailbreak)
        CRITICAL     // Confirmed compromise (e.g., modified system binaries)
    }

    /**
     * Integrity check result.
     */
    public static class IntegrityResult {
        private final boolean passed;
        private final IntegrityRisk risk;
        private final List<String> violations;
        private final Map<String, Object> details;

        public IntegrityResult(boolean passed, IntegrityRisk risk,
                                List<String> violations, Map<String, Object> details) {
            this.passed = passed;
            this.risk = risk;
            this.violations = violations;
            this.details = details;
        }

        public boolean isPassed() { return passed; }
        public IntegrityRisk getRisk() { return risk; }
        public List<String> getViolations() { return violations; }
        public Map<String, Object> getDetails() { return details; }

        public Map<String, Object> toMap() {
            return Map.of(
                    "passed", passed,
                    "risk", risk.name(),
                    "violations", violations,
                    "details", details
            );
        }
    }

    // ============================================================
    //  Jailbreak / Root Detection
    // ============================================================

    /**
     * Detect jailbreak on iOS devices based on reported indicators.
     */
    public IntegrityResult detectJailbreak(Map<String, Boolean> indicators) {
        List<String> violations = new ArrayList<>();
        int score = 0;

        // Check for common jailbreak indicators
        if (indicators.getOrDefault("cydia_installed", false)) {
            violations.add("Cydia package manager detected");
            score += 30;
        }
        if (indicators.getOrDefault("substrate_installed", false)) {
            violations.add("Cydia Substrate detected");
            score += 30;
        }
        if (indicators.getOrDefault("ssh_listening", false)) {
            violations.add("SSH server running");
            score += 20;
        }
        if (indicators.getOrDefault("sandbox_escaped", false)) {
            violations.add("Sandbox escape detected");
            score += 40;
        }
        if (indicators.getOrDefault("suspicious_files", false)) {
            violations.add("Suspicious system files found");
            score += 25;
        }
        if (indicators.getOrDefault("debugger_attached", false)) {
            violations.add("Debugger attached");
            score += 15;
        }

        return evaluateRisk(score, violations, "iOS");
    }

    /**
     * Detect root on Android devices based on reported indicators.
     */
    public IntegrityResult detectRoot(Map<String, Boolean> indicators) {
        List<String> violations = new ArrayList<>();
        int score = 0;

        if (indicators.getOrDefault("su_binary", false)) {
            violations.add("su binary found");
            score += 30;
        }
        if (indicators.getOrDefault("magisk_installed", false)) {
            violations.add("Magisk detected");
            score += 35;
        }
        if (indicators.getOrDefault("superuser_apk", false)) {
            violations.add("Superuser APK found");
            score += 25;
        }
        if (indicators.getOrDefault("busybox", false)) {
            violations.add("BusyBox installed");
            score += 15;
        }
        if (indicators.getOrDefault("rw_system", false)) {
            violations.add("System partition mounted R/W");
            score += 30;
        }
        if (indicators.getOrDefault("xposed", false)) {
            violations.add("Xposed framework detected");
            score += 25;
        }
        if (indicators.getOrDefault("safety_net_failed", false)) {
            violations.add("SafetyNet attestation failed");
            score += 20;
        }

        return evaluateRisk(score, violations, "Android");
    }

    /**
     * Detect root on Linux (QooBot onboard) based on reported indicators.
     */
    public IntegrityResult detectLinuxTampering(Map<String, Boolean> indicators) {
        List<String> violations = new ArrayList<>();
        int score = 0;

        if (indicators.getOrDefault("kernel_module_modified", false)) {
            violations.add("Kernel modules modified");
            score += 40;
        }
        if (indicators.getOrDefault("secure_boot_disabled", false)) {
            violations.add("Secure boot disabled");
            score += 35;
        }
        if (indicators.getOrDefault("selinux_permissive", false)) {
            violations.add("SELinux in permissive mode");
            score += 25;
        }
        if (indicators.getOrDefault("root_login_enabled", false)) {
            violations.add("Root SSH login enabled");
            score += 30;
        }
        if (indicators.getOrDefault("qoobot_binary_modified", false)) {
            violations.add("QooBot binaries modified");
            score += 50;
        }

        return evaluateRisk(score, violations, "Linux");
    }

    // ============================================================
    //  Client Binary Integrity
    // ============================================================

    /**
     * Verify client binary integrity using a hash chain.
     * The client sends hashes of its critical binaries, and we
     * compare against known-good hashes.
     */
    public IntegrityResult verifyBinaryIntegrity(Map<String, String> clientHashes,
                                                   Map<String, String> expectedHashes) {
        List<String> violations = new ArrayList<>();
        int score = 0;

        for (var expected : expectedHashes.entrySet()) {
            String binary = expected.getKey();
            String expectedHash = expected.getValue();
            String clientHash = clientHashes.get(binary);

            if (clientHash == null) {
                violations.add("Missing hash for: " + binary);
                score += 50;
            } else if (!constantTimeEquals(expectedHash, clientHash)) {
                violations.add("Hash mismatch for: " + binary);
                score += 50;
            }
        }

        // Check for unexpected binaries
        for (var client : clientHashes.entrySet()) {
            if (!expectedHashes.containsKey(client.getKey())) {
                violations.add("Unexpected binary: " + client.getKey());
                score += 20;
            }
        }

        return evaluateRisk(score, violations, "BinaryIntegrity");
    }

    /**
     * Verify .qooskills package integrity (tamper detection).
     */
    public IntegrityResult verifySkillPackageIntegrity(String packageHash,
                                                         String expectedHash,
                                                         String developerSignature) {
        List<String> violations = new ArrayList<>();
        int score = 0;

        if (!constantTimeEquals(expectedHash, packageHash)) {
            violations.add("Package hash mismatch — possible tampering");
            score += 80;
        }

        if (developerSignature == null || developerSignature.isEmpty()) {
            violations.add("Missing developer signature");
            score += 50;
        }

        return evaluateRisk(score, violations, "SkillPackage");
    }

    /**
     * Perform runtime environment integrity check.
     */
    public IntegrityResult checkRuntimeEnvironment(Map<String, Object> envInfo) {
        List<String> violations = new ArrayList<>();
        int score = 0;

        // Check for emulator
        if (Boolean.TRUE.equals(envInfo.getOrDefault("is_emulator", false))) {
            violations.add("Running in emulator");
            score += 15;
        }

        // Check for hooking frameworks
        if (Boolean.TRUE.equals(envInfo.getOrDefault("frida_detected", false))) {
            violations.add("Frida hooking framework detected");
            score += 40;
        }
        if (Boolean.TRUE.equals(envInfo.getOrDefault("substrate_hooked", false))) {
            violations.add("Cydia Substrate hooks detected");
            score += 40;
        }

        // Check app integrity
        if (Boolean.TRUE.equals(envInfo.getOrDefault("app_repackaged", false))) {
            violations.add("App appears to be repackaged");
            score += 60;
        }

        // Check if installed from official store
        String installSource = (String) envInfo.getOrDefault("install_source", "unknown");
        if (!"official_store".equals(installSource) && !"development".equals(installSource)) {
            violations.add("App installed from unofficial source: " + installSource);
            score += 30;
        }

        return evaluateRisk(score, violations, "RuntimeEnvironment");
    }

    // ============================================================
    //  Helper Methods
    // ============================================================

    private IntegrityResult evaluateRisk(int score, List<String> violations, String context) {
        IntegrityRisk risk;
        if (score == 0) {
            risk = IntegrityRisk.CLEAN;
        } else if (score < 20) {
            risk = IntegrityRisk.LOW;
        } else if (score < 50) {
            risk = IntegrityRisk.MEDIUM;
        } else if (score < 80) {
            risk = IntegrityRisk.HIGH;
        } else {
            risk = IntegrityRisk.CRITICAL;
        }

        boolean passed = risk == IntegrityRisk.CLEAN || risk == IntegrityRisk.LOW;

        Map<String, Object> details = new LinkedHashMap<>();
        details.put("score", score);
        details.put("context", context);
        details.put("checked_at", System.currentTimeMillis());

        if (risk != IntegrityRisk.CLEAN) {
            log.warn("Integrity check failed in {}: risk={}, score={}, violations={}",
                    context, risk, score, violations);
        }

        return new IntegrityResult(passed, risk, violations, details);
    }

    private boolean constantTimeEquals(String a, String b) {
        if (a.length() != b.length()) return false;
        int result = 0;
        for (int i = 0; i < a.length(); i++) {
            result |= a.charAt(i) ^ b.charAt(i);
        }
        return result == 0;
    }
}
