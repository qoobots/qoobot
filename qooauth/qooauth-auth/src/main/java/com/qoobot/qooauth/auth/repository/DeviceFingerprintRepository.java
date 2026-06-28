package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.DeviceFingerprint;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface DeviceFingerprintRepository extends JpaRepository<DeviceFingerprint, String> {

    Optional<DeviceFingerprint> findByUserIdAndFingerprintHash(String userId, String fingerprintHash);

    List<DeviceFingerprint> findByUserIdOrderByLastSeenAtDesc(String userId);

    List<DeviceFingerprint> findByRiskScoreGreaterThanEqual(double minScore);
}
