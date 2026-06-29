package com.qoobot.qooauth.auth.service;

import com.qoobot.qooauth.auth.entity.ConsentRecord;
import com.qoobot.qooauth.auth.entity.DataRetentionPolicy;
import com.qoobot.qooauth.auth.repository.ConsentRecordRepository;
import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.common.util.IdGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Privacy & Consent Management Service.
 * <p>
 * Implements GDPR/CCPA/PIPL compliance features:
 * <ul>
 *   <li>Consent collection and management</li>
 *   <li>Privacy labels for data processing transparency</li>
 *   <li>Data minimization enforcement</li>
 *   <li>Consent withdrawal and data deletion</li>
 *   <li>Data portability (GDPR Article 20)</li>
 * </ul>
 */
@Service
public class PrivacyConsentService {

    private static final Logger log = LoggerFactory.getLogger(PrivacyConsentService.class);

    private final ConsentRecordRepository consentRecordRepository;

    // Privacy labels (Apple-style privacy nutrition labels)
    private final Map<String, PrivacyLabel> privacyLabels = new ConcurrentHashMap<>();

    // Data retention policies
    private final Map<String, DataRetentionPolicy> retentionPolicies = new ConcurrentHashMap<>();

    // Standard processing purposes
    public static final String PURPOSE_ANALYTICS = "analytics";
    public static final String PURPOSE_PERSONALIZATION = "personalization";
    public static final String PURPOSE_LOCATION = "location";
    public static final String PURPOSE_ADVERTISING = "advertising";
    public static final String PURPOSE_DIAGNOSTICS = "diagnostics";
    public static final String PURPOSE_THIRD_PARTY = "third_party_sharing";
    public static final String PURPOSE_MARKETING = "marketing";

    public PrivacyConsentService(ConsentRecordRepository consentRecordRepository) {
        this.consentRecordRepository = consentRecordRepository;
        initializePrivacyLabels();
        initializeRetentionPolicies();
    }

    /**
     * Record user consent for a data processing purpose.
     */
    @Transactional
    public ConsentRecord recordConsent(String userId, String purpose, boolean granted,
                                        String ipAddress, String userAgent,
                                        String consentVersion, String privacyPolicyVersion) {
        // Revoke existing consent for this purpose
        ConsentRecord existing = consentRecordRepository
                .findByUserIdAndPurposeAndRevokedAtIsNull(userId, purpose)
                .orElse(null);

        if (existing != null) {
            existing.setRevokedAt(Instant.now());
            consentRecordRepository.save(existing);
        }

        ConsentRecord record = new ConsentRecord();
        record.setConsentId(IdGenerator.generateDeviceFingerprintId().replace("dfp_", "cns_"));
        record.setUserId(userId);
        record.setPurpose(purpose);
        record.setGranted(granted);
        record.setIpAddress(ipAddress);
        record.setUserAgent(userAgent);
        record.setConsentVersion(consentVersion);
        record.setPrivacyPolicyVersion(privacyPolicyVersion);
        record.setGrantedAt(Instant.now());
        record.setExpiresAt(Instant.now().plus(365, ChronoUnit.DAYS)); // 1 year

        return consentRecordRepository.save(record);
    }

    /**
     * Withdraw consent for a specific purpose.
     */
    @Transactional
    public void withdrawConsent(String userId, String purpose) {
        ConsentRecord consent = consentRecordRepository
                .findByUserIdAndPurposeAndRevokedAtIsNull(userId, purpose)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND,
                        "No active consent found for purpose: " + purpose));

        consent.setRevokedAt(Instant.now());
        consentRecordRepository.save(consent);
        log.info("Consent withdrawn: user={}, purpose={}", userId, purpose);
    }

    /**
     * Check if user has granted consent for a purpose.
     */
    public boolean hasConsent(String userId, String purpose) {
        return consentRecordRepository
                .findByUserIdAndPurposeAndRevokedAtIsNull(userId, purpose)
                .map(ConsentRecord::isGranted)
                .orElse(false);
    }

    /**
     * Get all active consents for a user.
     */
    public List<ConsentRecord> getActiveConsents(String userId) {
        return consentRecordRepository.findActiveConsents(userId, Instant.now());
    }

    /**
     * Get all consent history for a user.
     */
    public List<ConsentRecord> getConsentHistory(String userId) {
        return consentRecordRepository.findByUserIdOrderByGrantedAtDesc(userId);
    }

    /**
     * Get privacy label for a data type.
     */
    public PrivacyLabel getPrivacyLabel(String dataType) {
        return privacyLabels.getOrDefault(dataType, new PrivacyLabel(dataType, "unknown", "No label defined"));
    }

    /**
     * Get all privacy labels.
     */
    public Map<String, PrivacyLabel> getAllPrivacyLabels() {
        return Collections.unmodifiableMap(privacyLabels);
    }

    /**
     * Check data minimization compliance: whether a data type can be collected.
     */
    public boolean canCollectData(String dataType, String userId, String purpose) {
        // Check consent
        if (!hasConsent(userId, purpose)) {
            return false;
        }

        // Check retention policy
        DataRetentionPolicy policy = retentionPolicies.get(dataType);
        if (policy == null) {
            return true; // No policy defined = allowed
        }

        return policy.isAutoDelete();
    }

    /**
     * Get data retention policy for a data category.
     */
    public DataRetentionPolicy getRetentionPolicy(String dataCategory) {
        return retentionPolicies.get(dataCategory);
    }

    /**
     * Generate GDPR data portability export for a user.
     */
    public Map<String, Object> generateDataExport(String userId) {
        Map<String, Object> export = new LinkedHashMap<>();
        export.put("export_date", Instant.now().toString());
        export.put("user_id", userId);
        export.put("consents", getConsentHistory(userId));
        export.put("privacy_labels", getAllPrivacyLabels());
        return export;
    }

    /**
     * Revoke all consents for a user (for account deletion).
     */
    @Transactional
    public void revokeAllConsents(String userId) {
        List<ConsentRecord> active = getActiveConsents(userId);
        Instant now = Instant.now();
        for (ConsentRecord c : active) {
            c.setRevokedAt(now);
        }
        consentRecordRepository.saveAll(active);
        log.info("All consents revoked for user {}", userId);
    }

    // ========================================================================
    // Initialization
    // ========================================================================

    private void initializePrivacyLabels() {
        // Data used to track you
        privacyLabels.put("contact_info", new PrivacyLabel("contact_info", "Contact Info",
                "Name, email address, phone number", "Account management", false, false));
        privacyLabels.put("health_data", new PrivacyLabel("health_data", "Health & Fitness",
                "Health and fitness data", "Health monitoring features", true, true));
        privacyLabels.put("location", new PrivacyLabel("location", "Location",
                "Precise and coarse location", "Navigation and local services", true, false));
        privacyLabels.put("sensor_data", new PrivacyLabel("sensor_data", "Sensor Data",
                "Camera, microphone, LiDAR data", "Perception and interaction", true, true));
        privacyLabels.put("usage_data", new PrivacyLabel("usage_data", "Usage Data",
                "Product interaction, feature usage", "Product improvement", false, false));
        privacyLabels.put("diagnostics", new PrivacyLabel("diagnostics", "Diagnostics",
                "Crash logs, performance data", "Bug fixing and optimization", false, false));
        privacyLabels.put("identifiers", new PrivacyLabel("identifiers", "Identifiers",
                "User ID, device ID", "Account and device management", false, false));
        privacyLabels.put("purchases", new PrivacyLabel("purchases", "Purchases",
                "Purchase history, payment info", "Commerce and subscriptions", false, false));
    }

    private void initializeRetentionPolicies() {
        // Default retention policies
        DataRetentionPolicy loginHistory = new DataRetentionPolicy();
        loginHistory.setPolicyId("ret_login_history");
        loginHistory.setDataCategory("login_history");
        loginHistory.setRetentionDays(90);
        loginHistory.setAutoDelete(true);
        loginHistory.setLegalBasis("Legitimate interest - security");
        loginHistory.setDescription("Login attempt records for security monitoring");
        loginHistory.setCreatedAt(Instant.now());
        loginHistory.setUpdatedAt(Instant.now());
        retentionPolicies.put("login_history", loginHistory);

        DataRetentionPolicy auditLogs = new DataRetentionPolicy();
        auditLogs.setPolicyId("ret_audit_logs");
        auditLogs.setDataCategory("audit_logs");
        auditLogs.setRetentionDays(365);
        auditLogs.setAutoDelete(true);
        auditLogs.setLegalBasis("Legal obligation - compliance");
        auditLogs.setDescription("Audit logs for regulatory compliance");
        auditLogs.setCreatedAt(Instant.now());
        auditLogs.setUpdatedAt(Instant.now());
        retentionPolicies.put("audit_logs", auditLogs);

        DataRetentionPolicy sessionData = new DataRetentionPolicy();
        sessionData.setPolicyId("ret_session_data");
        sessionData.setDataCategory("session_data");
        sessionData.setRetentionDays(30);
        sessionData.setAutoDelete(true);
        sessionData.setLegalBasis("Legitimate interest - service operation");
        sessionData.setDescription("Active session and token data");
        sessionData.setCreatedAt(Instant.now());
        sessionData.setUpdatedAt(Instant.now());
        retentionPolicies.put("session_data", sessionData);
    }

    // ========================================================================
    // Data Classes
    // ========================================================================

    /**
     * Privacy label (Apple App Store style).
     */
    public static class PrivacyLabel {
        public final String dataType;
        public final String displayName;
        public final String description;
        public final boolean linkedToUser;
        public final boolean usedForTracking;
        public final List<String> purposes;

        public PrivacyLabel(String dataType, String displayName, String description) {
            this(dataType, displayName, description, false, false);
        }

        public PrivacyLabel(String dataType, String displayName, String description,
                             boolean linkedToUser, boolean usedForTracking) {
            this.dataType = dataType;
            this.displayName = displayName;
            this.description = description;
            this.linkedToUser = linkedToUser;
            this.usedForTracking = usedForTracking;
            this.purposes = new ArrayList<>();
        }
    }
}
