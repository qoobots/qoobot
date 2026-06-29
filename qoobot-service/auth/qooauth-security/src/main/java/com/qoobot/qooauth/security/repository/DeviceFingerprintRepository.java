package com.qoobot.qooauth.security.repository;

import com.qoobot.qooauth.security.entity.DeviceFingerprint;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Repository for DeviceFingerprint entity.
 */
@Repository
public interface DeviceFingerprintRepository extends JpaRepository<DeviceFingerprint, Long> {

    /**
     * Find a fingerprint by its hash.
     */
    Optional<DeviceFingerprint> findByFingerprintHash(String fingerprintHash);

    /**
     * Find all fingerprints associated with a user.
     */
    List<DeviceFingerprint> findByUserIdOrderByLastSeenAtDesc(String userId);

    /**
     * Find known devices for a user.
     */
    List<DeviceFingerprint> findByUserIdAndIsKnownTrue(String userId);
}
