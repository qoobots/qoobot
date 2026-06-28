package com.qoobot.qoostore.service;

import com.qoobot.qoostore.entity.*;
import com.qoobot.qoostore.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class LicenseService {

    private final LicenseRepository licenseRepository;
    private final SkillRepository skillRepository;
    private final SkillVersionRepository versionRepository;

    public List<License> getUserLicenses(UUID userId) {
        return licenseRepository.findByUserId(userId);
    }

    public List<License> getActiveUserLicenses(UUID userId) {
        return licenseRepository.findByUserIdAndStatus(userId, "active");
    }

    public License validateLicense(String licenseKey, String deviceId) {
        License license = licenseRepository.findByLicenseKey(licenseKey)
                .orElseThrow(() -> new RuntimeException("Invalid license key"));

        if (!"active".equals(license.getStatus())) {
            throw new RuntimeException("License is not active");
        }

        if (license.getExpiresAt() != null && license.getExpiresAt().isBefore(LocalDateTime.now())) {
            throw new RuntimeException("License has expired");
        }

        return license;
    }

    public List<License> getDeviceLicenses(String deviceId) {
        return licenseRepository.findByDeviceIdAndStatus(deviceId, "active");
    }

    @Transactional
    public void revokeLicense(String licenseKey) {
        License license = licenseRepository.findByLicenseKey(licenseKey)
                .orElseThrow(() -> new RuntimeException("License not found"));
        license.setStatus("revoked");
        licenseRepository.save(license);
        log.info("License revoked: licenseKey={}", licenseKey);
    }
}
