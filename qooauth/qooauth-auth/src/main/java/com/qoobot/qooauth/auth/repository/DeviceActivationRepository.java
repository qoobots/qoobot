package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.DeviceActivation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface DeviceActivationRepository extends JpaRepository<DeviceActivation, String> {

    Optional<DeviceActivation> findByDeviceSerial(String deviceSerial);

    Optional<DeviceActivation> findByDeviceId(String deviceId);

    Optional<DeviceActivation> findByActivationToken(String activationToken);

    List<DeviceActivation> findByUserId(String userId);

    List<DeviceActivation> findByActivationState(String activationState);

    Optional<DeviceActivation> findByDeviceIdAndActivationState(String deviceId, String activationState);

    Optional<DeviceActivation> findByDeviceSerialAndActivationState(String deviceSerial, String activationState);

    boolean existsByDeviceSerialAndActivationStateIn(String deviceSerial, List<String> states);

    @Modifying
    @Query("UPDATE DeviceActivation a SET a.activationState = :state, a.failureReason = :reason, a.updatedAt = :now WHERE a.activationId = :id")
    void updateState(@Param("id") String id, @Param("state") String state, @Param("reason") String reason, @Param("now") Instant now);

    @Modifying
    @Query("UPDATE DeviceActivation a SET a.activationState = 'EXPIRED', a.updatedAt = :now WHERE a.activationState IN ('PENDING', 'CHALLENGED') AND a.expiresAt < :now")
    int expirePendingActivations(@Param("now") Instant now);

    @Modifying
    @Query("UPDATE DeviceActivation a SET a.activationState = 'EXPIRED', a.updatedAt = :now WHERE a.challengeState = 'PENDING' AND a.challengeExpiresAt < :now")
    int expirePendingChallenges(@Param("now") Instant now);

    @Modifying
    @Query("UPDATE DeviceActivation a SET a.challengeAttempts = a.challengeAttempts + 1, a.updatedAt = :now WHERE a.activationId = :id")
    void incrementChallengeAttempts(@Param("id") String id, @Param("now") Instant now);

    @Modifying
    @Query("UPDATE DeviceActivation a SET a.activationState = :state, a.activatedAt = :activatedAt, a.updatedAt = :now WHERE a.activationId = :id")
    void markActivated(@Param("id") String id, @Param("state") String state, @Param("activatedAt") Instant activatedAt, @Param("now") Instant now);
}
