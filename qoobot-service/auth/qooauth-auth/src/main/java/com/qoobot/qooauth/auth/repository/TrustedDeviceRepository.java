package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.TrustedDevice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface TrustedDeviceRepository extends JpaRepository<TrustedDevice, String> {

    List<TrustedDevice> findByUserIdOrderByLastUsedAtDesc(String userId);

    Optional<TrustedDevice> findByUserIdAndFingerprint(String userId, String fingerprint);

    long countByUserId(String userId);

    void deleteByUserIdAndDeviceId(String userId, String deviceId);

    void deleteByUserId(String userId);
}
