package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.ApiKey;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface ApiKeyRepository extends JpaRepository<ApiKey, String> {

    List<ApiKey> findByUserIdAndState(String userId, String state);

    List<ApiKey> findByUserId(String userId);

    Optional<ApiKey> findByKeyHash(String keyHash);

    long countByUserIdAndState(String userId, String state);

    @Modifying
    @Query("UPDATE ApiKey k SET k.quotaUsed = k.quotaUsed + 1, k.lastUsedAt = :now WHERE k.keyId = :keyId")
    int incrementQuotaUsed(@Param("keyId") String keyId, @Param("now") Instant now);

    @Modifying
    @Query("UPDATE ApiKey k SET k.quotaUsed = 0, k.quotaResetAt = :newResetAt WHERE k.quotaResetAt <= :now")
    int resetMonthlyQuotas(@Param("now") Instant now, @Param("newResetAt") Instant newResetAt);

    @Modifying
    @Query("UPDATE ApiKey k SET k.state = 'EXPIRED' WHERE k.state = 'ACTIVE' AND k.expiresAt IS NOT NULL AND k.expiresAt <= :now")
    int expireOverdueKeys(@Param("now") Instant now);
}
