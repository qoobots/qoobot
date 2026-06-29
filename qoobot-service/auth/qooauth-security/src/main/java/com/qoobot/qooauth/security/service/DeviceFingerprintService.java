package com.qoobot.qooauth.security.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.qoobot.qooauth.security.entity.DeviceFingerprint;
import com.qoobot.qooauth.security.repository.DeviceFingerprintRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Map;
import java.util.Optional;

/**
 * Device fingerprinting service.
 * <p>
 * Implements browser/device fingerprinting via:
 * <ul>
 *   <li>Canvas hashing - GPU rendering variations produce unique canvas fingerprints</li>
 *   <li>WebGL hashing - GPU vendor/renderer information</li>
 *   <li>Font enumeration - installed font list as identifying feature</li>
 * </ul>
 * <p>
 * Computes composite fingerprint hash, risk scoring, and device spoofing detection.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DeviceFingerprintService {

    private static final double SPOOFING_RISK_THRESHOLD = 0.7;
    private static final double UNKNOWN_DEVICE_BASE_RISK = 0.4;

    private final DeviceFingerprintRepository deviceFingerprintRepository;
    private final ObjectMapper objectMapper;

    /**
     * Compute a composite fingerprint hash from device components.
     *
     * @param components map of fingerprint components (canvas, webgl, fonts, navigator, screen)
     * @return SHA-256 hash of the serialized components
     */
    public String computeFingerprintHash(Map<String, Object> components) {
        try {
            String serialized = objectMapper.writeValueAsString(components);
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(serialized.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize fingerprint components", e);
            throw new RuntimeException("Fingerprint computation failed", e);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }

    /**
     * Look up a fingerprint by hash.
     *
     * @param fingerprintHash the composite fingerprint hash
     * @return optional DeviceFingerprint entity
     */
    @Transactional(readOnly = true)
    public Optional<DeviceFingerprint> findByHash(String fingerprintHash) {
        return deviceFingerprintRepository.findByFingerprintHash(fingerprintHash);
    }

    /**
     * Register or update a device fingerprint.
     * Updates lastSeenAt if already exists, creates new record otherwise.
     *
     * @param userId          associated user ID (nullable)
     * @param fingerprintHash the composite hash
     * @param components      raw fingerprint components
     * @param isKnown         whether this is a known/trusted device
     * @return the saved DeviceFingerprint entity
     */
    @Transactional
    public DeviceFingerprint registerFingerprint(String userId, String fingerprintHash,
                                                  Map<String, Object> components, boolean isKnown) {
        String componentsJson = serializeComponents(components);
        double riskScore = evaluateDeviceRisk(fingerprintHash, components, isKnown);

        Optional<DeviceFingerprint> existing = deviceFingerprintRepository.findByFingerprintHash(fingerprintHash);
        if (existing.isPresent()) {
            DeviceFingerprint fp = existing.get();
            fp.setLastSeenAt(Instant.now());
            fp.setComponents(componentsJson);
            fp.setRiskScore(riskScore);
            if (userId != null) {
                fp.setUserId(userId);
            }
            if (isKnown) {
                fp.setIsKnown(true);
            }
            log.debug("Updated existing fingerprint: hash={}, riskScore={}", fingerprintHash, riskScore);
            return deviceFingerprintRepository.save(fp);
        }

        DeviceFingerprint fp = DeviceFingerprint.builder()
                .userId(userId)
                .fingerprintHash(fingerprintHash)
                .components(componentsJson)
                .riskScore(riskScore)
                .isKnown(isKnown)
                .firstSeenAt(Instant.now())
                .lastSeenAt(Instant.now())
                .build();

        log.info("Registered new device fingerprint: hash={}, riskScore={}, isKnown={}",
                fingerprintHash, riskScore, isKnown);
        return deviceFingerprintRepository.save(fp);
    }

    /**
     * Evaluate the risk level of a device fingerprint.
     * Higher score = more suspicious.
     *
     * @param fingerprintHash the fingerprint hash
     * @param components      the fingerprint components
     * @param isKnown         whether this is a known device
     * @return risk score [0.0, 1.0]
     */
    public double evaluateDeviceRisk(String fingerprintHash, Map<String, Object> components, boolean isKnown) {
        if (isKnown) {
            return 0.0; // Known trusted device
        }

        // Check for spoofing indicators
        double spoofingScore = detectSpoofing(components);

        // Base risk for unknown devices
        double riskScore = UNKNOWN_DEVICE_BASE_RISK + spoofingScore * 0.6;

        return Math.min(1.0, Math.max(0.0, riskScore));
    }

    /**
     * Detect device spoofing attempts.
     * Checks for inconsistencies between fingerprint components.
     *
     * @param components the fingerprint components
     * @return spoofing probability [0.0, 1.0]
     */
    public double detectSpoofing(Map<String, Object> components) {
        double spoofingIndicators = 0.0;

        // Check 1: Canvas fingerprint is empty or generic
        Object canvas = components.get("canvas");
        if (canvas == null || canvas.toString().isEmpty() || "data:,".equals(canvas.toString())) {
            spoofingIndicators += 0.3;
        }

        // Check 2: WebGL renderer is a known spoofed string
        Object webgl = components.get("webgl");
        if (webgl != null) {
            String webglStr = webgl.toString().toLowerCase();
            if (webglStr.contains("swiftshader") || webglStr.contains("llvmpipe")
                    || webglStr.contains("virtual") || webglStr.contains("microsoft basic render")) {
                spoofingIndicators += 0.4;
            }
        } else {
            spoofingIndicators += 0.3;
        }

        // Check 3: Font list is suspiciously short
        @SuppressWarnings("unchecked")
        Object fonts = components.get("fonts");
        if (fonts instanceof java.util.List) {
            int fontCount = ((java.util.List<?>) fonts).size();
            if (fontCount < 5) {
                spoofingIndicators += 0.3;
            }
        } else if (fonts == null) {
            spoofingIndicators += 0.2;
        }

        // Check 4: Navigator properties show automation
        Object navigator = components.get("navigator");
        if (navigator instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> nav = (Map<String, Object>) navigator;
            Object webdriver = nav.get("webdriver");
            if (webdriver != null && !"false".equals(webdriver.toString()) && !"undefined".equals(webdriver.toString())) {
                spoofingIndicators += 0.5;
            }
        }

        return Math.min(1.0, spoofingIndicators);
    }

    private String serializeComponents(Map<String, Object> components) {
        if (components == null) return null;
        try {
            return objectMapper.writeValueAsString(components);
        } catch (JsonProcessingException e) {
            log.warn("Failed to serialize fingerprint components: {}", e.getMessage());
            return null;
        }
    }
}
