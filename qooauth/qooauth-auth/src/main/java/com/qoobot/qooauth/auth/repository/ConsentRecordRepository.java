package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.ConsentRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface ConsentRecordRepository extends JpaRepository<ConsentRecord, String> {

    List<ConsentRecord> findByUserIdOrderByGrantedAtDesc(String userId);

    Optional<ConsentRecord> findByUserIdAndPurposeAndRevokedAtIsNull(String userId, String purpose);

    @Query("SELECT c FROM ConsentRecord c WHERE c.userId = :userId AND c.granted = true AND " +
           "c.revokedAt IS NULL AND (c.expiresAt IS NULL OR c.expiresAt > :now)")
    List<ConsentRecord> findActiveConsents(@Param("userId") String userId, @Param("now") Instant now);

    @Query("SELECT c FROM ConsentRecord c WHERE c.expiresAt IS NOT NULL AND c.expiresAt < :now AND c.revokedAt IS NULL")
    List<ConsentRecord> findExpiredConsents(@Param("now") Instant now);
}
