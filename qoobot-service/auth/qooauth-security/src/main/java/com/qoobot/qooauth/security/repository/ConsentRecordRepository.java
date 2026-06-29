package com.qoobot.qooauth.security.repository;

import com.qoobot.qooauth.security.entity.ConsentRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Repository for ConsentRecord entity.
 */
@Repository
public interface ConsentRecordRepository extends JpaRepository<ConsentRecord, Long> {

    /**
     * Find the latest consent record for a specific user and consent type.
     */
    Optional<ConsentRecord> findTopByUserIdAndConsentTypeOrderByCreatedAtDesc(String userId, String consentType);

    /**
     * Find all consent records for a user.
     */
    List<ConsentRecord> findByUserIdOrderByCreatedAtDesc(String userId);

    /**
     * Find all currently granted consents for a user.
     */
    List<ConsentRecord> findByUserIdAndGrantedTrueAndRevokedAtIsNull(String userId);
}
