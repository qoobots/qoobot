package com.qoobot.qooauth.security.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Map;

/**
 * Device and platform integrity verification service.
 * <p>
 * Provides:
 * <ul>
 *   <li>Jailbreak/root detection - checks for signs of compromised OS</li>
 *   <li>Binary integrity verification - hash-based application integrity checks</li>
 *   <li>TPM PCR validation stubs - placeholder for hardware attestation</li>
 * </ul>
 * <p>
 * Note: TPM PCR validation requires platform-specific native libraries.
 * The stubs here define the interface for future hardware attestation integration.
 */
@Slf4j
@Service
public class IntegrityService {

    /**
     * Verify device integrity by checking for jailbreak/root indicators.
     *
     * @param platform       the device platform ("ANDROID", "IOS", "LINUX", "WINDOWS")
     * @param indicators     platform-specific integrity indicators
     * @return verification result
     */
    public Map<String, Object> verifyIntegrity(String platform, Map<String, Object> indicators) {
        log.info("Verifying device integrity for platform: {}", platform);

        boolean jailbreakDetected = detectJailbreak(platform, indicators);
        boolean binaryIntegrityOk = verifyBinaryIntegrity(indicators);
        boolean tpmOk = validateTpmPcr(indicators);

        boolean overallPassed = !jailbreakDetected && binaryIntegrityOk && tpmOk;
        String status = overallPassed ? "PASSED" : "FAILED";

        if (!overallPassed) {
            log.warn("Integrity check FAILED: platform={}, jailbreak={}, binaryOk={}, tpmOk={}",
                    platform, jailbreakDetected, binaryIntegrityOk, tpmOk);
        }

        return Map.of(
                "status", status,
                "platform", platform,
                "checks", Map.of(
                        "jailbreakDetection", Map.of(
                                "passed", !jailbreakDetected,
                                "detected", jailbreakDetected
                        ),
                        "binaryIntegrity", Map.of(
                                "passed", binaryIntegrityOk
                        ),
                        "tpmAttestation", Map.of(
                                "passed", tpmOk,
                                "note", "TPM PCR validation stub - requires hardware attestation integration"
                        )
                )
        );
    }

    /**
     * Detect jailbreak or root on the device.
     */
    private boolean detectJailbreak(String platform, Map<String, Object> indicators) {
        if (indicators == null) return false;

        return switch (platform.toUpperCase()) {
            case "ANDROID" -> detectAndroidRoot(indicators);
            case "IOS" -> detectIosJailbreak(indicators);
            case "LINUX" -> detectLinuxRoot(indicators);
            case "WINDOWS" -> detectWindowsCompromise(indicators);
            default -> false;
        };
    }

    private boolean detectAndroidRoot(Map<String, Object> indicators) {
        // Check for common root indicators
        boolean hasRootBinaries = containsKeyTrue(indicators, "su_binary")
                || containsKeyTrue(indicators, "magisk_detected")
                || containsKeyTrue(indicators, "supersu_detected");
        boolean hasRootProps = containsKeyTrue(indicators, "ro_debuggable")
                || containsKeyTrue(indicators, "ro_secure_0");
        boolean hasSelinuxDisabled = containsKeyTrue(indicators, "selinux_disabled");
        boolean hasTestKeys = containsKeyTrue(indicators, "test_keys_signing");

        return hasRootBinaries || hasRootProps || hasSelinuxDisabled || hasTestKeys;
    }

    private boolean detectIosJailbreak(Map<String, Object> indicators) {
        return containsKeyTrue(indicators, "cydia_installed")
                || containsKeyTrue(indicators, "substrate_detected")
                || containsKeyTrue(indicators, "ssh_listening")
                || containsKeyTrue(indicators, "sandbox_escape");
    }

    private boolean detectLinuxRoot(Map<String, Object> indicators) {
        return containsKeyTrue(indicators, "uid_zero")
                || containsKeyTrue(indicators, "kernel_tainted");
    }

    private boolean detectWindowsCompromise(Map<String, Object> indicators) {
        return containsKeyTrue(indicators, "admin_privileges")
                || containsKeyTrue(indicators, "debugger_attached")
                || containsKeyTrue(indicators, "unsigned_drivers");
    }

    /**
     * Verify application binary integrity via hash comparison.
     */
    private boolean verifyBinaryIntegrity(Map<String, Object> indicators) {
        if (indicators == null) return true; // No binary info provided = pass

        String expectedHash = (String) indicators.get("expected_binary_hash");
        String actualHash = (String) indicators.get("actual_binary_hash");

        if (expectedHash == null || actualHash == null) return true;

        return expectedHash.equals(actualHash);
    }

    /**
     * TPM PCR validation stub.
     * In production, this would:
     * 1. Request TPM quote from device
     * 2. Verify quote signature against known good PCR values
     * 3. Check PCR bank consistency
     * 4. Validate against a reference integrity manifest
     */
    private boolean validateTpmPcr(Map<String, Object> indicators) {
        if (indicators == null) return true; // No TPM info provided = pass (stub)
        Boolean tpmAvailable = (Boolean) indicators.get("tpm_available");
        if (tpmAvailable == null || !tpmAvailable) return true; // No TPM = skip

        // Stub: In production, validate PCR quote signature and compare PCR values
        log.debug("TPM PCR validation stub invoked - returning pass for now");
        return true;
    }

    /**
     * Compute SHA-256 hash of binary content for integrity verification.
     */
    public String computeBinaryHash(byte[] binaryContent) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(binaryContent);
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }

    private boolean containsKeyTrue(Map<String, Object> map, String key) {
        Object value = map.get(key);
        if (value instanceof Boolean) return (Boolean) value;
        if (value instanceof String) return "true".equalsIgnoreCase((String) value);
        return false;
    }
}
