package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.ActivationChallenge;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface ActivationChallengeRepository extends JpaRepository<ActivationChallenge, String> {

    List<ActivationChallenge> findByActivationId(String activationId);

    Optional<ActivationChallenge> findByActivationIdAndChallengeState(String activationId, String challengeState);

    List<ActivationChallenge> findByDeviceIdAndChallengeState(String deviceId, String challengeState);

    Optional<ActivationChallenge> findByActivationIdAndChallengeNonce(String activationId, String challengeNonce);

    @Modifying
    @Query("UPDATE ActivationChallenge c SET c.challengeState = :state WHERE c.activationId = :activationId AND c.challengeState = 'PENDING'")
    void expireByActivationId(@Param("activationId") String activationId, @Param("state") String state);

    @Modifying
    @Query("UPDATE ActivationChallenge c SET c.challengeState = 'EXPIRED' WHERE c.challengeState = 'PENDING' AND c.expiresAt < :now")
    int expirePendingChallenges(@Param("now") Instant now);
}
