package com.qoobot.qooauth.security.service;

import com.qoobot.qooauth.security.entity.PrivacyLabel;
import com.qoobot.qooauth.security.repository.PrivacyLabelRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;

/**
 * Privacy label management service.
 * <p>
 * Manages privacy labels for data classification and compliance:
 * <ul>
 *   <li>Privacy label CRUD operations</li>
 *   <li>Data classification by category and type</li>
 *   <li>Retention policy enforcement - identifies data past retention period</li>
 * </ul>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class PrivacyService {

    private final PrivacyLabelRepository privacyLabelRepository;

    /**
     * Create a new privacy label.
     */
    @Transactional
    public PrivacyLabel createLabel(PrivacyLabel label) {
        PrivacyLabel saved = privacyLabelRepository.save(label);
        log.info("Created privacy label: id={}, category={}, dataType={}",
                saved.getId(), saved.getLabelCategory(), saved.getDataType());
        return saved;
    }

    /**
     * Get all privacy labels.
     */
    @Transactional(readOnly = true)
    public List<PrivacyLabel> getAllLabels() {
        return privacyLabelRepository.findAll();
    }

    /**
     * Find privacy labels by category.
     */
    @Transactional(readOnly = true)
    public List<PrivacyLabel> getLabelsByCategory(String labelCategory) {
        return privacyLabelRepository.findByLabelCategory(labelCategory);
    }

    /**
     * Update an existing privacy label.
     */
    @Transactional
    public PrivacyLabel updateLabel(Long id, PrivacyLabel updated) {
        PrivacyLabel existing = privacyLabelRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Privacy label not found: " + id));

        existing.setLabelCategory(updated.getLabelCategory());
        existing.setDataType(updated.getDataType());
        existing.setCollectionPurpose(updated.getCollectionPurpose());
        existing.setIsOptional(updated.getIsOptional());
        existing.setRetentionDays(updated.getRetentionDays());

        PrivacyLabel saved = privacyLabelRepository.save(existing);
        log.info("Updated privacy label: id={}", id);
        return saved;
    }

    /**
     * Delete a privacy label.
     */
    @Transactional
    public void deleteLabel(Long id) {
        privacyLabelRepository.deleteById(id);
        log.info("Deleted privacy label: id={}", id);
    }

    /**
     * Classify data by type and return applicable privacy labels.
     *
     * @param dataType the type of data to classify
     * @return list of applicable privacy labels
     */
    @Transactional(readOnly = true)
    public List<PrivacyLabel> classifyData(String dataType) {
        // Find all labels where dataType matches (broad match)
        return privacyLabelRepository.findAll().stream()
                .filter(label -> label.getDataType().equalsIgnoreCase(dataType)
                        || label.getDataType().equals("*"))
                .toList();
    }

    /**
     * Check which data items have exceeded their retention period.
     *
     * @return list of expired privacy labels
     */
    @Transactional(readOnly = true)
    public List<PrivacyLabel> findExpiredRetentions() {
        return privacyLabelRepository.findAll().stream()
                .filter(label -> {
                    if (label.getRetentionDays() < 0) return false; // Indefinite retention
                    Instant cutoff = Instant.now().minusSeconds(
                            (long) label.getRetentionDays() * 24 * 60 * 60);
                    return label.getCreatedAt().isBefore(cutoff);
                })
                .toList();
    }

    /**
     * Enforce retention policy - mark or handle data past retention period.
     * In production, this would trigger data deletion/anonymization workflows.
     *
     * @return count of records requiring retention action
     */
    @Transactional(readOnly = true)
    public int enforceRetentionPolicy() {
        List<PrivacyLabel> expired = findExpiredRetentions();
        log.info("Retention enforcement: {} labels have exceeded retention period", expired.size());
        return expired.size();
    }
}
