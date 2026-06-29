package com.qoobot.qooauth.auth.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.spec.X509EncodedKeySpec;
import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Secure Boot Chain Service.
 * <p>
 * Implements hardware root of trust and secure boot verification:
 * <ul>
 *   <li>Boot image signing and verification chain</li>
 *   <li>Anti-rollback protection with version counters</li>
 *   <li>Secure boot state attestation</li>
 *   <li>Measured boot with TPM/PCR integration</li>
 * </ul>
 * <p>
 * Boot Chain: BootROM → SPL → U-Boot → Linux Kernel → RootFS → User Apps
 */
@Service
public class SecureBootService {

    private static final Logger log = LoggerFactory.getLogger(SecureBootService.class);

    private final RedisTemplate<String, String> redisTemplate;

    // Root of trust key (in production, stored in HSM/fuses)
    private final PublicKey rootOfTrustPublicKey;
    private final PrivateKey rootOfTrustPrivateKey;

    // Anti-rollback version counters (per-device)
    private static final String VERSION_COUNTER_KEY = "qooauth:secureboot:version:";
    private static final String BOOT_STATE_KEY = "qooauth:secureboot:state:";

    // Supported boot stages
    public enum BootStage {
        BOOTROM("bootrom", 0),
        SPL("spl", 1),
        UBOOT("uboot", 2),
        LINUX_KERNEL("linux", 3),
        ROOTFS("rootfs", 4),
        USER_APPS("user_apps", 5);

        public final String name;
        public final int order;

        BootStage(String name, int order) {
            this.name = name;
            this.order = order;
        }
    }

    public SecureBootService(RedisTemplate<String, String> redisTemplate) {
        this.redisTemplate = redisTemplate;
        try {
            KeyPairGenerator keyGen = KeyPairGenerator.getInstance("EC");
            keyGen.initialize(256);
            KeyPair rootKey = keyGen.generateKeyPair();
            this.rootOfTrustPublicKey = rootKey.getPublic();
            this.rootOfTrustPrivateKey = rootKey.getPrivate();
            log.info("Secure boot root of trust initialized");
        } catch (Exception e) {
            throw new RuntimeException("Failed to initialize secure boot root of trust", e);
        }
    }

    /**
     * Sign a boot stage image with ECDSA.
     *
     * @param deviceId     device identifier
     * @param stage        boot stage
     * @param imageHash    SHA-256 hash of the boot image
     * @param version      version number (must be >= current anti-rollback counter)
     * @return signature bytes
     */
    public byte[] signBootImage(String deviceId, BootStage stage, byte[] imageHash, int version) throws Exception {
        // Check anti-rollback
        int currentVersion = getAntiRollbackVersion(deviceId, stage);
        if (version < currentVersion) {
            throw new SecurityException(String.format(
                    "Anti-rollback: version %d < current %d for stage %s",
                    version, currentVersion, stage.name));
        }

        // Build signing payload
        byte[] payload = buildSigningPayload(deviceId, stage, imageHash, version);

        // Sign with root of trust
        Signature sig = Signature.getInstance("SHA256withECDSA");
        sig.initSign(rootOfTrustPrivateKey);
        sig.update(payload);
        byte[] signature = sig.sign();

        // Update anti-rollback counter
        setAntiRollbackVersion(deviceId, stage, version);

        log.info("Signed boot image: device={}, stage={}, version={}", deviceId, stage.name, version);
        return signature;
    }

    /**
     * Verify a boot stage image signature.
     *
     * @param deviceId     device identifier
     * @param stage        boot stage
     * @param imageHash    SHA-256 hash of the boot image
     * @param version      version number
     * @param signature    the signature to verify
     * @return true if signature is valid
     */
    public boolean verifyBootImage(String deviceId, BootStage stage, byte[] imageHash,
                                    int version, byte[] signature) throws Exception {
        // Check anti-rollback
        int currentVersion = getAntiRollbackVersion(deviceId, stage);
        if (version < currentVersion) {
            log.warn("Anti-rollback violation: device={}, stage={}, version={} < current={}",
                    deviceId, stage.name, version, currentVersion);
            return false;
        }

        // Build verification payload
        byte[] payload = buildSigningPayload(deviceId, stage, imageHash, version);

        // Verify signature
        Signature sig = Signature.getInstance("SHA256withECDSA");
        sig.initVerify(rootOfTrustPublicKey);
        sig.update(payload);
        return sig.verify(signature);
    }

    /**
     * Record boot state attestation.
     *
     * @param deviceId    device identifier
     * @param stage       boot stage that completed
     * @param success     whether the stage booted successfully
     * @param pcrValues   TPM PCR measurements
     */
    public void recordBootState(String deviceId, BootStage stage, boolean success,
                                 Map<Integer, String> pcrValues) {
        String key = BOOT_STATE_KEY + deviceId;
        Map<String, String> state = new HashMap<>();
        state.put("stage", stage.name);
        state.put("stage_order", String.valueOf(stage.order));
        state.put("success", String.valueOf(success));
        state.put("timestamp", Instant.now().toString());
        if (pcrValues != null) {
            for (Map.Entry<Integer, String> e : pcrValues.entrySet()) {
                state.put("pcr_" + e.getKey(), e.getValue());
            }
        }

        // Store in Redis with TTL
        for (Map.Entry<String, String> entry : state.entrySet()) {
            redisTemplate.opsForHash().put(key, entry.getKey(), entry.getValue());
        }
        redisTemplate.expire(key, Duration.ofHours(1));

        log.info("Boot state recorded: device={}, stage={}, success={}", deviceId, stage.name, success);
    }

    /**
     * Get current boot state for a device.
     */
    public Map<String, String> getBootState(String deviceId) {
        String key = BOOT_STATE_KEY + deviceId;
        Map<Object, Object> entries = redisTemplate.opsForHash().entries(key);
        Map<String, String> result = new HashMap<>();
        for (Map.Entry<Object, Object> e : entries.entrySet()) {
            result.put(String.valueOf(e.getKey()), String.valueOf(e.getValue()));
        }
        return result;
    }

    /**
     * Check if device has a verified secure boot chain.
     */
    public boolean isSecureBootVerified(String deviceId) {
        Map<String, String> state = getBootState(deviceId);
        String success = state.get("success");
        String stage = state.get("stage");
        return "true".equals(success) && BootStage.USER_APPS.name.equals(stage);
    }

    /**
     * Get the anti-rollback version counter for a stage.
     */
    public int getAntiRollbackVersion(String deviceId, BootStage stage) {
        String key = VERSION_COUNTER_KEY + deviceId + ":" + stage.name;
        String val = redisTemplate.opsForValue().get(key);
        return val != null ? Integer.parseInt(val) : 0;
    }

    /**
     * Set the anti-rollback version counter.
     */
    private void setAntiRollbackVersion(String deviceId, BootStage stage, int version) {
        String key = VERSION_COUNTER_KEY + deviceId + ":" + stage.name;
        redisTemplate.opsForValue().set(key, String.valueOf(version));
    }

    /**
     * Build signing payload: deviceId || stage || imageHash || version
     */
    private byte[] buildSigningPayload(String deviceId, BootStage stage, byte[] imageHash, int version) {
        byte[] deviceIdBytes = deviceId.getBytes(StandardCharsets.UTF_8);
        byte[] stageBytes = stage.name.getBytes(StandardCharsets.UTF_8);
        byte[] versionBytes = String.valueOf(version).getBytes(StandardCharsets.UTF_8);

        int totalLen = deviceIdBytes.length + stageBytes.length + imageHash.length + versionBytes.length + 12;
        byte[] payload = new byte[totalLen];
        int offset = 0;

        System.arraycopy(deviceIdBytes, 0, payload, offset, deviceIdBytes.length);
        offset += deviceIdBytes.length;

        System.arraycopy(stageBytes, 0, payload, offset, stageBytes.length);
        offset += stageBytes.length;

        System.arraycopy(imageHash, 0, payload, offset, imageHash.length);
        offset += imageHash.length;

        System.arraycopy(versionBytes, 0, payload, offset, versionBytes.length);

        return payload;
    }

    /**
     * Compute SHA-256 hash of image bytes.
     */
    public byte[] hashImage(byte[] imageBytes) throws NoSuchAlgorithmException {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        return digest.digest(imageBytes);
    }
}
