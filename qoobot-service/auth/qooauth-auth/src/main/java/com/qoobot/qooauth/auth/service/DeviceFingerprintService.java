package com.qoobot.qooauth.auth.service;

import com.qoobot.qooauth.auth.entity.DeviceFingerprint;
import com.qoobot.qooauth.auth.repository.DeviceFingerprintRepository;
import com.qoobot.qooauth.common.util.IdGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

/**
 * Device Fingerprint Service.
 * <p>
 * Tracks device identity across sessions using browser fingerprinting:
 * <ul>
 *   <li>Canvas fingerprint — browser rendering differences</li>
 *   <li>WebGL fingerprint — GPU renderer variations</li>
 *   <li>Font fingerprint — installed system fonts</li>
 *   <li>Screen resolution, timezone, language</li>
 * </ul>
 * <p>
 * Used for:
 * <ul>
 *   <li>Recognizing returning devices</li>
 *   <li>Detecting device spoofing (inconsistent fingerprint components)</li>
 *   <li>Identifying suspicious new devices</li>
 *   <li>Risk scoring for fraud detection</li>
 * </ul>
 */
@Service
public class DeviceFingerprintService {

    private static final Logger log = LoggerFactory.getLogger(DeviceFingerprintService.class);

    private final DeviceFingerprintRepository deviceFingerprintRepository;

    // Risk scoring weights
    private static final double NEW_DEVICE_BASELINE_RISK = 0.2;
    private static final double INCONSISTENT_FINGERPRINT_RISK = 0.5;
    private static final double RARE_OS_RISK = 0.1;
    private static final double SPOOFED_BROWSER_RISK = 0.6;

    public DeviceFingerprintService(DeviceFingerprintRepository deviceFingerprintRepository) {
        this.deviceFingerprintRepository = deviceFingerprintRepository;
    }

    /**
     * Record or update a device fingerprint for a user.
     *
     * @param userId           the user ID
     * @param deviceType       browser / mobile_app / desktop / robot
     * @param browserName      e.g., "Chrome", "Firefox"
     * @param browserVersion   e.g., "120.0.6099"
     * @param osName           e.g., "Windows", "macOS"
     * @param osVersion        e.g., "11", "14.2"
     * @param screenResolution e.g., "1920x1080"
     * @param timezoneOffset   UTC offset in minutes
     * @param language         browser language
     * @param canvasHash       canvas rendering hash
     * @param webglHash        WebGL renderer hash
     * @param fontHash         installed fonts hash
     * @return the DeviceFingerprint entity
     */
    @Transactional
    public DeviceFingerprint recordFingerprint(String userId, String deviceType,
                                                String browserName, String browserVersion,
                                                String osName, String osVersion,
                                                String screenResolution, int timezoneOffset,
                                                String language, String canvasHash,
                                                String webglHash, String fontHash) {
        // Generate composite fingerprint hash
        String fingerprintHash = generateCompositeHash(
                canvasHash, webglHash, fontHash, osName, browserName);

        // Check if device already known
        Optional<DeviceFingerprint> existing = deviceFingerprintRepository
                .findByUserIdAndFingerprintHash(userId, fingerprintHash);

        if (existing.isPresent()) {
            // Update existing record
            DeviceFingerprint fp = existing.get();
            fp.setLastSeenAt(Instant.now());
            fp.setUseCount(fp.getUseCount() + 1);
            fp.setBrowserVersion(browserVersion);
            fp.setOsVersion(osVersion);
            fp.setScreenResolution(screenResolution);
            fp.setRiskScore(calculateRiskScore(fp, false));
            return deviceFingerprintRepository.save(fp);
        }

        // Create new fingerprint record
        DeviceFingerprint fp = new DeviceFingerprint();
        fp.setFingerprintId(IdGenerator.generateDeviceFingerprintId());
        fp.setUserId(userId);
        fp.setFingerprintHash(fingerprintHash);
        fp.setDeviceType(deviceType);
        fp.setBrowserName(browserName);
        fp.setBrowserVersion(browserVersion);
        fp.setOsName(osName);
        fp.setOsVersion(osVersion);
        fp.setScreenResolution(screenResolution);
        fp.setTimezoneOffset(timezoneOffset);
        fp.setLanguage(language);
        fp.setCanvasHash(canvasHash);
        fp.setWebglHash(webglHash);
        fp.setFontHash(fontHash);
        fp.setFirstSeenAt(Instant.now());
        fp.setLastSeenAt(Instant.now());
        fp.setUseCount(1);
        fp.setRiskScore(NEW_DEVICE_BASELINE_RISK);
        fp.setCreatedAt(Instant.now());

        return deviceFingerprintRepository.save(fp);
    }

    /**
     * Get all fingerprint records for a user.
     */
    public List<DeviceFingerprint> getUserFingerprints(String userId) {
        return deviceFingerprintRepository.findByUserIdOrderByLastSeenAtDesc(userId);
    }

    /**
     * Check if a device fingerprint is known for a user.
     */
    public boolean isKnownDevice(String userId, String canvasHash, String webglHash,
                                  String fontHash, String osName, String browserName) {
        String hash = generateCompositeHash(canvasHash, webglHash, fontHash, osName, browserName);
        return deviceFingerprintRepository.findByUserIdAndFingerprintHash(userId, hash).isPresent();
    }

    /**
     * Get high-risk device fingerprints.
     */
    public List<DeviceFingerprint> getHighRiskFingerprints(double minScore) {
        return deviceFingerprintRepository.findByRiskScoreGreaterThanEqual(minScore);
    }

    /**
     * Calculate risk score for a device fingerprint.
     */
    private double calculateRiskScore(DeviceFingerprint fp, boolean isNew) {
        double score = 0.0;

        if (isNew) {
            score += NEW_DEVICE_BASELINE_RISK;
        }

        // Inconsistent fingerprint components (e.g., Chrome on Linux is rare for consumers)
        if (fp.getBrowserName() != null && fp.getOsName() != null) {
            String combo = fp.getBrowserName().toLowerCase() + "|" + fp.getOsName().toLowerCase();
            if (combo.contains("safari") && !combo.contains("mac") && !combo.contains("ios")) {
                score += SPOOFED_BROWSER_RISK; // Safari on non-Apple = spoofed
            }
        }

        return Math.min(1.0, score);
    }

    /**
     * Generate a composite SHA-256 hash from multiple fingerprint components.
     */
    private String generateCompositeHash(String canvasHash, String webglHash,
                                          String fontHash, String osName, String browserName) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            String input = String.join("|",
                    canvasHash != null ? canvasHash : "",
                    webglHash != null ? webglHash : "",
                    fontHash != null ? fontHash : "",
                    osName != null ? osName : "",
                    browserName != null ? browserName : "");
            byte[] digest = md.digest(input.getBytes(StandardCharsets.UTF_8));
            return bytesToHex(digest);
        } catch (NoSuchAlgorithmException e) {
            log.error("SHA-256 not available", e);
            return "error";
        }
    }

    private String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}
