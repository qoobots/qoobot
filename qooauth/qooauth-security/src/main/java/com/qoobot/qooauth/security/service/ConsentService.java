package com.qoobot.qooauth.security.service;

import com.qoobot.qooauth.security.dto.ConsentRequest;
import com.qoobot.qooauth.security.entity.ConsentRecord;
import com.qoobot.qooauth.security.repository.ConsentRecordRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

/**
 * GDPR/CCPA/PIPL consent lifecycle management service.
 * <p>
 * Manages the full consent lifecycle:
 * <ul>
 *   <li><b>Informed consent recording</b> - records user consent with policy version</li>
 *   <li><b>Consent withdrawal</b> - records revocation with timestamp</li>
 *   <li><b>Compliance versioning</b> - tracks consent by policy version for audit</li>
 * </ul>
 * <p>
 * Supports multiple consent types:
 * DATA_COLLECTION, MARKETING, THIRD_PARTY_SHARING, COOKIES, ANALYTICS, BIOMETRIC, etc.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ConsentService {

    private final ConsentRecordRepository consentRecordRepository;

    /**
     * Grant consent for a user.
     * Records the consent action with policy version for compliance audit.
     *
     * @param request the consent grant request
     * @return the created consent record
     */
    @Transactional
    public ConsentRecord grantConsent(ConsentRequest request) {
        // Check for existing active consent
        Optional<ConsentRecord> existing = consentRecordRepository
                .findTopByUserIdAndConsentTypeOrderByCreatedAtDesc(
                        request.getUserId(), request.getConsentType());

        // If an active grant exists with the same version, no need to re-record
        if (existing.isPresent() && existing.get().getGranted()
                && existing.get().getVersion().equals(request.getVersion())) {
            log.debug("Consent already granted: userId={}, type={}, version={}",
                    request.getUserId(), request.getConsentType(), request.getVersion());
            return existing.get();
        }

        Instant now = Instant.now();
        ConsentRecord record = ConsentRecord.builder()
                .userId(request.getUserId())
                .consentType(request.getConsentType())
                .version(request.getVersion())
                .granted(true)
                .grantedAt(now)
                .revokedAt(null)
                .ipAddress(request.getIpAddress())
                .build();

        ConsentRecord saved = consentRecordRepository.save(record);
        log.info("Consent granted: userId={}, type={}, version={}",
                request.getUserId(), request.getConsentType(), request.getVersion());
        return saved;
    }

    /**
     * Revoke consent for a user.
     * Sets revokedAt on the latest active consent record.
     *
     * @param request the consent revocation request
     * @return the updated consent record
     */
    @Transactional
    public ConsentRecord revokeConsent(ConsentRequest request) {
        Optional<ConsentRecord> existing = consentRecordRepository
                .findTopByUserIdAndConsentTypeOrderByCreatedAtDesc(
                        request.getUserId(), request.getConsentType());

        if (existing.isEmpty()) {
            // No prior consent record - create a revocation record
            ConsentRecord record = ConsentRecord.builder()
                    .userId(request.getUserId())
                    .consentType(request.getConsentType())
                    .version(request.getVersion())
                    .granted(false)
                    .revokedAt(Instant.now())
                    .ipAddress(request.getIpAddress())
                    .build();

            ConsentRecord saved = consentRecordRepository.save(record);
            log.info("Consent revocation recorded (no prior grant): userId={}, type={}",
                    request.getUserId(), request.getConsentType());
            return saved;
        }

        ConsentRecord record = existing.get();
        if (!record.getGranted() && record.getRevokedAt() != null) {
            log.debug("Consent already revoked: userId={}, type={}",
                    request.getUserId(), request.getConsentType());
            return record;
        }

        record.setGranted(false);
        record.setRevokedAt(Instant.now());
        record.setVersion(request.getVersion());
        if (request.getIpAddress() != null) {
            record.setIpAddress(request.getIpAddress());
        }

        ConsentRecord saved = consentRecordRepository.save(record);
        log.info("Consent revoked: userId={}, type={}, version={}",
                request.getUserId(), request.getConsentType(), request.getVersion());
        return saved;
    }

    /**
     * Get all consent records for a user.
     */
    @Transactional(readOnly = true)
    public List<ConsentRecord> getUserConsents(String userId) {
        return consentRecordRepository.findByUserIdOrderByCreatedAtDesc(userId);
    }

    /**
     * Get currently active (granted, not revoked) consents for a user.
     */
    @Transactional(readOnly = true)
    public List<ConsentRecord> getActiveConsents(String userId) {
        return consentRecordRepository.findByUserIdAndGrantedTrueAndRevokedAtIsNull(userId);
    }

    /**
     * Check if a user has granted consent for a specific type.
     */
    @Transactional(readOnly = true)
    public boolean hasConsent(String userId, String consentType) {
        Optional<ConsentRecord> record = consentRecordRepository
                .findTopByUserIdAndConsentTypeOrderByCreatedAtDesc(userId, consentType);
        return record.isPresent() && record.get().getGranted() && record.get().getRevokedAt() == null;
    }

    /**
     * Get the current consent version for a specific type.
     */
    @Transactional(readOnly = true)
    public Optional<String> getConsentVersion(String userId, String consentType) {
        return consentRecordRepository
                .findTopByUserIdAndConsentTypeOrderByCreatedAtDesc(userId, consentType)
                .filter(r -> r.getGranted() && r.getRevokedAt() == null)
                .map(ConsentRecord::getVersion);
    }

    /**
     * Delete all consent records for a user (GDPR right to erasure).
     */
    @Transactional
    public int deleteUserConsents(String userId) {
        List<ConsentRecord> records = consentRecordRepository.findByUserIdOrderByCreatedAtDesc(userId);
        consentRecordRepository.deleteAll(records);
        log.info("Deleted all consent records for user: {}, count={}", userId, records.size());
        return records.size();
    }
}
