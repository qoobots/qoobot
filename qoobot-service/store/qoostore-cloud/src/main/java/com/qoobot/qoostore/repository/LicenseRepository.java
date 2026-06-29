package com.qoobot.qoostore.repository;

import com.qoobot.qoostore.entity.License;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface LicenseRepository extends JpaRepository<License, Long> {
    Optional<License> findByLicenseKey(String licenseKey);
    List<License> findByUserId(UUID userId);
    List<License> findByUserIdAndStatus(UUID userId, String status);
    Optional<License> findByUserIdAndSkillIdAndDeviceId(UUID userId, Long skillId, String deviceId);
    List<License> findByDeviceIdAndStatus(String deviceId, String status);
}
