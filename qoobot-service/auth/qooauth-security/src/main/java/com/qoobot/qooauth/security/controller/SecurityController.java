package com.qoobot.qooauth.security.controller;

import com.qoobot.qooauth.security.dto.ConsentRequest;
import com.qoobot.qooauth.security.dto.SecurityEventResponse;
import com.qoobot.qooauth.security.dto.ThreatDetectionRequest;
import com.qoobot.qooauth.security.entity.ConsentRecord;
import com.qoobot.qooauth.security.entity.DeviceFingerprint;
import com.qoobot.qooauth.security.entity.PrivacyLabel;
import com.qoobot.qooauth.security.entity.SecurityEvent;
import com.qoobot.qooauth.security.repository.SecurityEventRepository;
import com.qoobot.qooauth.security.service.*;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Security and privacy REST controller.
 * <p>
 * Provides endpoints for:
 * <ul>
 *   <li>Health check</li>
 *   <li>Threat detection and analysis</li>
 *   <li>Privacy label management</li>
 *   <li>Consent lifecycle (GDPR/CCPA/PIPL)</li>
 *   <li>Device fingerprinting</li>
 *   <li>Security event querying</li>
 *   <li>Platform integrity verification</li>
 * </ul>
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/security")
@RequiredArgsConstructor
public class SecurityController {

    private final ThreatDetectionService threatDetectionService;
    private final CredentialStuffingService credentialStuffingService;
    private final DeviceFingerprintService deviceFingerprintService;
    private final IntegrityService integrityService;
    private final EncryptionService encryptionService;
    private final PrivacyService privacyService;
    private final ConsentService consentService;
    private final SecurityEventRepository securityEventRepository;

    // ---- Health ----

    /**
     * Health check endpoint.
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        return ResponseEntity.ok(Map.of(
                "status", "UP",
                "service", "qooauth-security",
                "timestamp", java.time.Instant.now().toString()
        ));
    }

    // ---- Threat Detection ----

    /**
     * Analyze a login attempt for threat detection.
     * Returns composite risk score across 6 dimensions with recommended action.
     */
    @PostMapping("/threat/analyze")
    public ResponseEntity<Map<String, Object>> analyzeThreat(
            @Valid @RequestBody ThreatDetectionRequest request) {
        log.info("Threat analysis requested for user: {}", request.getUserId());
        Map<String, Object> result = threatDetectionService.analyzeLoginThreat(request);
        return ResponseEntity.ok(result);
    }

    // ---- Privacy Labels ----

    /**
     * Get all privacy labels.
     */
    @GetMapping("/privacy-labels")
    public ResponseEntity<List<PrivacyLabel>> getPrivacyLabels(
            @RequestParam(required = false) String category) {
        if (category != null && !category.isBlank()) {
            return ResponseEntity.ok(privacyService.getLabelsByCategory(category));
        }
        return ResponseEntity.ok(privacyService.getAllLabels());
    }

    // ---- Consent Management ----

    /**
     * Grant user consent.
     */
    @PostMapping("/consent/grant")
    public ResponseEntity<Map<String, Object>> grantConsent(
            @Valid @RequestBody ConsentRequest request) {
        log.info("Consent grant requested: userId={}, type={}", request.getUserId(), request.getConsentType());
        ConsentRecord record = consentService.grantConsent(request);
        return ResponseEntity.ok(Map.of(
                "status", "GRANTED",
                "userId", record.getUserId(),
                "consentType", record.getConsentType(),
                "version", record.getVersion(),
                "grantedAt", record.getGrantedAt().toString()
        ));
    }

    /**
     * Revoke user consent.
     */
    @PostMapping("/consent/revoke")
    public ResponseEntity<Map<String, Object>> revokeConsent(
            @Valid @RequestBody ConsentRequest request) {
        log.info("Consent revoke requested: userId={}, type={}", request.getUserId(), request.getConsentType());
        ConsentRecord record = consentService.revokeConsent(request);
        return ResponseEntity.ok(Map.of(
                "status", "REVOKED",
                "userId", record.getUserId(),
                "consentType", record.getConsentType(),
                "version", record.getVersion(),
                "revokedAt", record.getRevokedAt() != null ? record.getRevokedAt().toString() : null
        ));
    }

    /**
     * Get consent records for a user.
     */
    @GetMapping("/consents")
    public ResponseEntity<List<ConsentRecord>> getConsents(
            @RequestParam String userId) {
        log.debug("Fetching consents for user: {}", userId);
        return ResponseEntity.ok(consentService.getUserConsents(userId));
    }

    // ---- Device Fingerprint ----

    /**
     * Look up a device fingerprint by hash.
     */
    @GetMapping("/fingerprint/{hash}")
    public ResponseEntity<Map<String, Object>> getFingerprint(
            @PathVariable String hash) {
        log.debug("Fingerprint lookup: hash={}", hash);
        Optional<DeviceFingerprint> fp = deviceFingerprintService.findByHash(hash);
        if (fp.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        DeviceFingerprint f = fp.get();
        return ResponseEntity.ok(Map.of(
                "fingerprintHash", f.getFingerprintHash(),
                "userId", f.getUserId(),
                "riskScore", f.getRiskScore(),
                "isKnown", f.getIsKnown(),
                "firstSeenAt", f.getFirstSeenAt().toString(),
                "lastSeenAt", f.getLastSeenAt().toString()
        ));
    }

    /**
     * Evaluate a device fingerprint and register/update it.
     */
    @PostMapping("/fingerprint/evaluate")
    public ResponseEntity<Map<String, Object>> evaluateFingerprint(
            @RequestBody Map<String, Object> request) {
        String userId = (String) request.get("userId");
        @SuppressWarnings("unchecked")
        Map<String, Object> components = (Map<String, Object>) request.get("components");
        Boolean isKnown = request.get("isKnown") instanceof Boolean b ? b : false;

        if (components == null || components.isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of("error", "components are required"));
        }

        String hash = deviceFingerprintService.computeFingerprintHash(components);
        double riskScore = deviceFingerprintService.evaluateDeviceRisk(hash, components, isKnown);
        double spoofingScore = deviceFingerprintService.detectSpoofing(components);

        DeviceFingerprint saved = deviceFingerprintService.registerFingerprint(
                userId, hash, components, isKnown);

        return ResponseEntity.ok(Map.of(
                "fingerprintHash", hash,
                "riskScore", Math.round(riskScore * 1000.0) / 1000.0,
                "spoofingProbability", Math.round(spoofingScore * 1000.0) / 1000.0,
                "isKnown", saved.getIsKnown(),
                "action", riskScore >= 0.7 ? "WARN" : "ACCEPT"
        ));
    }

    // ---- Security Events ----

    /**
     * Query security events with optional filters.
     */
    @GetMapping("/events")
    public ResponseEntity<List<SecurityEventResponse>> getEvents(
            @RequestParam(required = false) String userId,
            @RequestParam(required = false) String eventType,
            @RequestParam(required = false) String severity) {

        List<SecurityEvent> events = new ArrayList<>();
        if (userId != null) {
            events = securityEventRepository.findByUserIdOrderByDetectedAtDesc(userId);
        } else if (eventType != null) {
            events = securityEventRepository.findByEventTypeOrderByDetectedAtDesc(eventType);
        } else if (severity != null) {
            events = securityEventRepository.findBySeverityOrderByDetectedAtDesc(severity);
        } else {
            events = securityEventRepository.findAll();
        }

        List<SecurityEventResponse> responses = events.stream()
                .map(this::toResponse)
                .toList();
        return ResponseEntity.ok(responses);
    }

    private SecurityEventResponse toResponse(SecurityEvent event) {
        return SecurityEventResponse.builder()
                .id(event.getId())
                .userId(event.getUserId())
                .eventType(event.getEventType())
                .severity(event.getSeverity())
                .sourceIp(event.getSourceIp())
                .details(parseDetails(event.getDetails()))
                .detectedAt(event.getDetectedAt().toString())
                .resolvedAt(event.getResolvedAt() != null ? event.getResolvedAt().toString() : null)
                .resolved(event.getResolvedAt() != null)
                .build();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseDetails(String detailsJson) {
        if (detailsJson == null) return null;
        try {
            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            return mapper.readValue(detailsJson, Map.class);
        } catch (Exception e) {
            log.warn("Failed to parse security event details: {}", e.getMessage());
            return Map.of("raw", detailsJson);
        }
    }

    // ---- Integrity Verification ----

    /**
     * Verify platform/device integrity.
     */
    @PostMapping("/integrity/verify")
    public ResponseEntity<Map<String, Object>> verifyIntegrity(
            @RequestBody Map<String, Object> request) {
        String platform = (String) request.getOrDefault("platform", "UNKNOWN");
        @SuppressWarnings("unchecked")
        Map<String, Object> indicators = (Map<String, Object>) request.get("indicators");

        log.info("Integrity verification requested for platform: {}", platform);
        Map<String, Object> result = integrityService.verifyIntegrity(platform, indicators);
        return ResponseEntity.ok(result);
    }
}
