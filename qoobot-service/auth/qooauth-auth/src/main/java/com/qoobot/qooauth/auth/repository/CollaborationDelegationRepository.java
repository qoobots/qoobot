package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.CollaborationDelegation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface CollaborationDelegationRepository extends JpaRepository<CollaborationDelegation, String> {

    Optional<CollaborationDelegation> findByTokenHash(String tokenHash);

    List<CollaborationDelegation> findByDelegatorDeviceId(String delegatorDeviceId);

    List<CollaborationDelegation> findByDelegateDeviceId(String delegateDeviceId);

    List<CollaborationDelegation> findByDelegateDeviceIdAndState(String delegateDeviceId, String state);

    @Query("SELECT d FROM CollaborationDelegation d WHERE d.state = 'ACTIVE' AND d.expiresAt < :now")
    List<CollaborationDelegation> findExpiredActive(@Param("now") Instant now);

    @Query("SELECT d FROM CollaborationDelegation d WHERE d.delegatorDeviceId = :deviceId AND d.state = 'ACTIVE'")
    List<CollaborationDelegation> findActiveByDelegator(@Param("deviceId") String deviceId);

    @Query("SELECT d FROM CollaborationDelegation d WHERE d.delegateDeviceId = :deviceId AND d.state = 'ACTIVE'")
    List<CollaborationDelegation> findActiveByDelegate(@Param("deviceId") String deviceId);

    @Modifying
    @Query("UPDATE CollaborationDelegation d SET d.state = 'REVOKED', d.revokedAt = CURRENT_TIMESTAMP, d.revokeReason = :reason WHERE d.delegationId = :delegationId")
    void revokeDelegation(@Param("delegationId") String delegationId, @Param("reason") String reason);

    @Modifying
    @Query("UPDATE CollaborationDelegation d SET d.state = 'EXPIRED' WHERE d.state = 'ACTIVE' AND d.expiresAt < :now")
    int expireDelegations(@Param("now") Instant now);
}
