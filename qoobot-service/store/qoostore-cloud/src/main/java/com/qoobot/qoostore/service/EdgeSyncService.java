package com.qoobot.qoostore.service;

import com.qoobot.qoostore.entity.*;
import com.qoobot.qoostore.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class EdgeSyncService {

    private final DeviceSkillRepository deviceSkillRepository;
    private final SkillRepository skillRepository;
    private final SkillVersionRepository versionRepository;
    private final LicenseRepository licenseRepository;

    public List<DeviceSkill> getDeviceSkills(String deviceId) {
        return deviceSkillRepository.findByDeviceId(deviceId);
    }

    @Transactional
    public DeviceSkill installSkill(String deviceId, String skillId, String licenseKey) {
        Skill skill = skillRepository.findBySkillId(skillId)
                .orElseThrow(() -> new RuntimeException("Skill not found: " + skillId));

        License license = licenseRepository.findByLicenseKey(licenseKey)
                .orElseThrow(() -> new RuntimeException("License not found"));

        if (!"active".equals(license.getStatus())) {
            throw new RuntimeException("License is not active");
        }

        if (deviceSkillRepository.findByDeviceIdAndSkillId(deviceId, skill.getId()).isPresent()) {
            throw new RuntimeException("Skill already installed on this device");
        }

        SkillVersion latestVersion = versionRepository.findBySkillIdOrderByCreatedAtDesc(skill.getId())
                .stream().findFirst()
                .orElseThrow(() -> new RuntimeException("No version available"));

        DeviceSkill deviceSkill = DeviceSkill.builder()
                .deviceId(deviceId)
                .skillId(skill.getId())
                .versionId(latestVersion.getId())
                .licenseId(license.getId())
                .status("installed")
                .installedAt(LocalDateTime.now())
                .build();
        deviceSkill = deviceSkillRepository.save(deviceSkill);

        license.setDeviceId(deviceId);
        licenseRepository.save(license);

        log.info("Skill installed: deviceId={}, skillId={}, version={}", deviceId, skillId, latestVersion.getVersion());
        return deviceSkill;
    }

    @Transactional
    public DeviceSkill updateSkill(String deviceId, String skillId) {
        Skill skill = skillRepository.findBySkillId(skillId)
                .orElseThrow(() -> new RuntimeException("Skill not found: " + skillId));

        DeviceSkill deviceSkill = deviceSkillRepository.findByDeviceIdAndSkillId(deviceId, skill.getId())
                .orElseThrow(() -> new RuntimeException("Skill not installed on this device"));

        SkillVersion latestVersion = versionRepository.findBySkillIdOrderByCreatedAtDesc(skill.getId())
                .stream().findFirst()
                .orElseThrow(() -> new RuntimeException("No version available"));

        deviceSkill.setVersionId(latestVersion.getId());
        deviceSkill.setStatus("active");
        deviceSkill.setUpdatedAt(LocalDateTime.now());
        deviceSkill = deviceSkillRepository.save(deviceSkill);

        log.info("Skill updated: deviceId={}, skillId={}, newVersion={}", deviceId, skillId, latestVersion.getVersion());
        return deviceSkill;
    }

    @Transactional
    public void uninstallSkill(String deviceId, String skillId) {
        Skill skill = skillRepository.findBySkillId(skillId)
                .orElseThrow(() -> new RuntimeException("Skill not found: " + skillId));

        DeviceSkill deviceSkill = deviceSkillRepository.findByDeviceIdAndSkillId(deviceId, skill.getId())
                .orElseThrow(() -> new RuntimeException("Skill not installed on this device"));

        deviceSkill.setStatus("removed");
        deviceSkill.setUpdatedAt(LocalDateTime.now());
        deviceSkillRepository.save(deviceSkill);

        log.info("Skill uninstalled: deviceId={}, skillId={}", deviceId, skillId);
    }

    public String getDownloadUrl(String skillId, String deviceId) {
        Skill skill = skillRepository.findBySkillId(skillId)
                .orElseThrow(() -> new RuntimeException("Skill not found: " + skillId));

        SkillVersion latestVersion = versionRepository.findBySkillIdOrderByCreatedAtDesc(skill.getId())
                .stream().findFirst()
                .orElseThrow(() -> new RuntimeException("No version available"));

        return latestVersion.getPackageUrl();
    }
}
