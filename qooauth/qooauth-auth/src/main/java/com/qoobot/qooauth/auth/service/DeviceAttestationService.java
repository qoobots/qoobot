package com.qoobot.qooauth.auth.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.*;

/**
 * Device Attestation & Accessory Authentication Service.
 *
 * Provides:
 * - Remote Attestation (RA-TLS) — prove device integrity to a remote verifier
 * - Hardware fingerprint collection for device identity
 * - Made for QooBot (MFQ) accessory authentication via identity chips
 */
@Service
public class DeviceAttestationService {
    private static final Logger log = LoggerFactory.getLogger(DeviceAttestationService.class);

    private final SecureRandom secureRandom = new SecureRandom();

    /**
     * Known-good Platform Configuration Register (PCR) values
     * for verified firmware versions.
     */
    private final Map<String, List<String>> knownGoodPcrs = new HashMap<>();

    /**
     * Registered MFQ accessories.
     */
    private final Map<String, MfqAccessory> registeredAccessories = new HashMap<>();

    public DeviceAttestationService() {
        initializeKnownGoodPcrs();
    }

    // ============================================================
    //  Remote Attestation (RA-TLS)
    // ============================================================

    /**
     * Generate an attestation challenge for a device.
     * The device must respond with TPM-signed PCR values and a quote.
     */
    public AttestationChallenge generateChallenge(String deviceId, String verifierId) {
        AttestationChallenge challenge = new AttestationChallenge();
        challenge.challengeId = UUID.randomUUID().toString();
        challenge.deviceId = deviceId;
        challenge.verifierId = verifierId;
        challenge.nonce = generateNonce();
        challenge.createdAt = Instant.now();
        challenge.expiresAt = Instant.now().plusSeconds(300); // 5 minute validity

        log.info("Attestation challenge {} generated for device {}", challenge.challengeId, deviceId);
        return challenge;
    }

    /**
     * Verify an attestation response from a device.
     *
     * @param challengeId The original challenge ID
     * @param pcrValues Map of PCR index to measured value
     * @param tpmQuote TPM-signed quote over PCR values
     * @param tpmSignature TPM signature
     * @param firmwareVersion Device firmware version
     */
    public AttestationResult verifyAttestation(String challengeId, String deviceId,
                                                 Map<Integer, String> pcrValues,
                                                 String tpmQuote, String tpmSignature,
                                                 String firmwareVersion) {
        List<String> violations = new ArrayList<>();
        boolean passed = true;

        // 1. Verify TPM quote (simplified — production uses TPM2_Quote verification)
        if (tpmQuote == null || tpmSignature == null) {
            violations.add("Missing TPM quote or signature");
            passed = false;
        }

        // 2. Verify PCR values against known-good values
        List<String> expectedPcrs = knownGoodPcrs.get(firmwareVersion);
        if (expectedPcrs == null) {
            violations.add("Unknown firmware version: " + firmwareVersion);
            passed = false;
        } else {
            for (int i = 0; i < expectedPcrs.size(); i++) {
                String expected = expectedPcrs.get(i);
                String actual = pcrValues.get(i);
                if (actual != null && !constantTimeEquals(expected, actual)) {
                    violations.add("PCR[" + i + "] mismatch: expected " +
                            expected.substring(0, 8) + "... got " +
                            (actual != null ? actual.substring(0, 8) : "null") + "...");
                    passed = false;
                }
            }
        }

        // 3. Verify nonce freshness
        // (In production, check that the nonce in the quote matches the challenge)

        AttestationResult result = new AttestationResult();
        result.challengeId = challengeId;
        result.deviceId = deviceId;
        result.passed = passed;
        result.violations = violations;
        result.firmwareVersion = firmwareVersion;
        result.verifiedAt = Instant.now();

        if (passed) {
            log.info("Attestation passed for device {} (firmware {})", deviceId, firmwareVersion);
        } else {
            log.warn("Attestation FAILED for device {}: {}", deviceId, violations);
        }

        return result;
    }

    /**
     * Register known-good PCR values for a firmware version.
     */
    public void registerKnownGoodPcrs(String firmwareVersion, List<String> pcrValues) {
        knownGoodPcrs.put(firmwareVersion, pcrValues);
        log.info("Registered known-good PCRs for firmware version {}", firmwareVersion);
    }

    // ============================================================
    //  Hardware Fingerprint Collection
    // ============================================================

    /**
     * Collect a hardware fingerprint for device identification.
     * Combines multiple hardware characteristics into a stable identifier.
     */
    public HardwareFingerprint collectFingerprint(String deviceId,
                                                    Map<String, String> hardwareInfo) {
        HardwareFingerprint fp = new HardwareFingerprint();
        fp.deviceId = deviceId;
        fp.cpuSerial = hardwareInfo.get("cpu_serial");
        fp.boardSerial = hardwareInfo.get("board_serial");
        fp.macAddresses = hardwareInfo.get("mac_addresses");
        fp.tpmEndorsementKey = hardwareInfo.get("tpm_ek_hash");
        fp.socModel = hardwareInfo.get("soc_model");
        fp.memorySerial = hardwareInfo.get("memory_serial");

        // Generate composite fingerprint hash
        String composite = deviceId +
                (fp.cpuSerial != null ? fp.cpuSerial : "") +
                (fp.boardSerial != null ? fp.boardSerial : "") +
                (fp.tpmEndorsementKey != null ? fp.tpmEndorsementKey : "");
        fp.compositeHash = sha256(composite);

        fp.collectedAt = Instant.now();

        log.debug("Hardware fingerprint collected for device {}: hash={}", deviceId, fp.compositeHash);
        return fp;
    }

    /**
     * Verify that a hardware fingerprint matches the expected value.
     */
    public boolean verifyFingerprint(String deviceId, String expectedHash,
                                      Map<String, String> currentHardwareInfo) {
        HardwareFingerprint current = collectFingerprint(deviceId, currentHardwareInfo);
        return constantTimeEquals(expectedHash, current.compositeHash);
    }

    // ============================================================
    //  MFQ Accessory Authentication
    // ============================================================

    /**
     * Register a Made for QooBot (MFQ) accessory.
     */
    public MfqAccessory registerAccessory(String accessoryId, String manufacturerId,
                                            String modelId, String serialNumber,
                                            String authChipId, String authChipPublicKey) {
        MfqAccessory acc = new MfqAccessory();
        acc.accessoryId = accessoryId;
        acc.manufacturerId = manufacturerId;
        acc.modelId = modelId;
        acc.serialNumber = serialNumber;
        acc.authChipId = authChipId;
        acc.authChipPublicKey = authChipPublicKey;
        acc.status = "REGISTERED";
        acc.registeredAt = Instant.now();
        acc.certificationLevel = "MFQ_CERTIFIED";

        registeredAccessories.put(accessoryId, acc);
        log.info("MFQ accessory registered: {} ({} by {})", accessoryId, modelId, manufacturerId);
        return acc;
    }

    /**
     * Authenticate an MFQ accessory using challenge-response.
     */
    public AccessoryAuthResult authenticateAccessory(String accessoryId, String challenge,
                                                       String response, String signature) {
        MfqAccessory acc = registeredAccessories.get(accessoryId);
        if (acc == null) {
            return AccessoryAuthResult.failed("Unknown accessory: " + accessoryId);
        }

        if (!"REGISTERED".equals(acc.status) && !"ACTIVE".equals(acc.status)) {
            return AccessoryAuthResult.failed("Accessory not in valid state: " + acc.status);
        }

        // Verify challenge-response (simplified — production uses ECDSA)
        String expectedResponse = sha256(challenge + acc.authChipId);
        boolean challengeOk = constantTimeEquals(expectedResponse,
                response != null ? response : "");

        if (!challengeOk) {
            log.warn("MFQ accessory {} challenge-response failed", accessoryId);
            return AccessoryAuthResult.failed("Challenge-response verification failed");
        }

        acc.lastAuthenticated = Instant.now();
        registeredAccessories.put(accessoryId, acc);

        log.info("MFQ accessory {} authenticated successfully", accessoryId);
        return AccessoryAuthResult.success(accessoryId, acc.manufacturerId, acc.modelId,
                acc.certificationLevel);
    }

    /**
     * Revoke an MFQ accessory.
     */
    public void revokeAccessory(String accessoryId, String reason) {
        MfqAccessory acc = registeredAccessories.get(accessoryId);
        if (acc != null) {
            acc.status = "REVOKED";
            acc.revokedAt = Instant.now();
            acc.revokeReason = reason;
            registeredAccessories.put(accessoryId, acc);
            log.warn("MFQ accessory {} revoked: {}", accessoryId, reason);
        }
    }

    /**
     * Get accessory information.
     */
    public MfqAccessory getAccessory(String accessoryId) {
        return registeredAccessories.get(accessoryId);
    }

    // ============================================================
    //  Helper Methods
    // ============================================================

    private void initializeKnownGoodPcrs() {
        // v1.0.0 firmware — initial release
        knownGoodPcrs.put("1.0.0", List.of(
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", // PCR0: BIOS
                "a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a", // PCR1: BIOS Config
                "6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d", // PCR2: Option ROM
                "b2a5d8e9c0f1a3b6d7e4f5c6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5"  // PCR3: Bootloader
        ));

        // v1.1.0 firmware — security patch
        knownGoodPcrs.put("1.1.0", List.of(
                "f1c2d3e4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1",
                "b2a3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2",
                "c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
                "d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4"
        ));
    }

    private String generateNonce() {
        byte[] bytes = new byte[32];
        secureRandom.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private String sha256(String data) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(data.getBytes());
            StringBuilder sb = new StringBuilder();
            for (byte b : hash) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (Exception e) {
            return "";
        }
    }

    private boolean constantTimeEquals(String a, String b) {
        if (a.length() != b.length()) return false;
        int result = 0;
        for (int i = 0; i < a.length(); i++) {
            result |= a.charAt(i) ^ b.charAt(i);
        }
        return result == 0;
    }

    // ============================================================
    //  DTOs
    // ============================================================

    public static class AttestationChallenge {
        public String challengeId;
        public String deviceId;
        public String verifierId;
        public String nonce;
        public Instant createdAt;
        public Instant expiresAt;

        public Map<String, Object> toMap() {
            return Map.of(
                    "challenge_id", challengeId,
                    "device_id", deviceId,
                    "nonce", nonce,
                    "created_at", createdAt.toString(),
                    "expires_at", expiresAt.toString()
            );
        }
    }

    public static class AttestationResult {
        public String challengeId;
        public String deviceId;
        public boolean passed;
        public List<String> violations;
        public String firmwareVersion;
        public Instant verifiedAt;

        public Map<String, Object> toMap() {
            return Map.of(
                    "challenge_id", challengeId,
                    "device_id", deviceId,
                    "passed", passed,
                    "violations", violations != null ? violations : List.of(),
                    "firmware_version", firmwareVersion != null ? firmwareVersion : "",
                    "verified_at", verifiedAt.toString()
            );
        }
    }

    public static class HardwareFingerprint {
        public String deviceId;
        public String cpuSerial;
        public String boardSerial;
        public String macAddresses;
        public String tpmEndorsementKey;
        public String socModel;
        public String memorySerial;
        public String compositeHash;
        public Instant collectedAt;

        public Map<String, Object> toMap() {
            return Map.of(
                    "device_id", deviceId,
                    "composite_hash", compositeHash,
                    "soc_model", socModel != null ? socModel : "",
                    "collected_at", collectedAt.toString()
            );
        }
    }

    public static class MfqAccessory {
        public String accessoryId;
        public String manufacturerId;
        public String modelId;
        public String serialNumber;
        public String authChipId;
        public String authChipPublicKey;
        public String status;
        public String certificationLevel;
        public Instant registeredAt;
        public Instant lastAuthenticated;
        public Instant revokedAt;
        public String revokeReason;

        public Map<String, Object> toMap() {
            return Map.of(
                    "accessory_id", accessoryId,
                    "manufacturer_id", manufacturerId,
                    "model_id", modelId,
                    "serial_number", serialNumber,
                    "status", status,
                    "certification_level", certificationLevel,
                    "registered_at", registeredAt.toString(),
                    "last_authenticated", lastAuthenticated != null ? lastAuthenticated.toString() : null
            );
        }
    }

    public static class AccessoryAuthResult {
        public boolean authenticated;
        public String reason;
        public String accessoryId;
        public String manufacturerId;
        public String modelId;
        public String certificationLevel;

        public static AccessoryAuthResult success(String id, String mfr, String model, String cert) {
            AccessoryAuthResult r = new AccessoryAuthResult();
            r.authenticated = true;
            r.accessoryId = id;
            r.manufacturerId = mfr;
            r.modelId = model;
            r.certificationLevel = cert;
            return r;
        }

        public static AccessoryAuthResult failed(String reason) {
            AccessoryAuthResult r = new AccessoryAuthResult();
            r.authenticated = false;
            r.reason = reason;
            return r;
        }

        public Map<String, Object> toMap() {
            return Map.of(
                    "authenticated", authenticated,
                    "reason", reason != null ? reason : "",
                    "accessory_id", accessoryId != null ? accessoryId : "",
                    "manufacturer_id", manufacturerId != null ? manufacturerId : "",
                    "model_id", modelId != null ? modelId : "",
                    "certification_level", certificationLevel != null ? certificationLevel : ""
            );
        }
    }
}
