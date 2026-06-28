package com.qoobot.qoostore.service;

import com.qoobot.qoostore.entity.*;
import com.qoobot.qoostore.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.core.RocketMQTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class PublisherService {

    private final SkillRepository skillRepository;
    private final SkillVersionRepository versionRepository;
    private final SubmissionRepository submissionRepository;
    private final DeveloperRepository developerRepository;
    private final StorageService storageService;
    private final RocketMQTemplate rocketMQTemplate;

    @Transactional
    public Skill submitSkill(Long developerId, String skillId, String name,
                              String description, Long categoryId, String tagline,
                              MultipartFile packageFile, String manifestJson) {

        Developer developer = developerRepository.findById(developerId)
                .orElseThrow(() -> new RuntimeException("Developer not found"));

        if (skillRepository.findBySkillId(skillId).isPresent()) {
            throw new RuntimeException("Skill ID already exists: " + skillId);
        }

        String packageUrl = storageService.uploadPackage(skillId, "1.0.0", packageFile);
        long packageSize = packageFile.getSize();

        Skill skill = Skill.builder()
                .skillId(skillId)
                .name(name)
                .developerId(developerId)
                .categoryId(categoryId)
                .tagline(tagline)
                .description(description)
                .status("draft")
                .build();
        skill = skillRepository.save(skill);

        SkillVersion version = SkillVersion.builder()
                .skillId(skill.getId())
                .version("1.0.0")
                .packageUrl(packageUrl)
                .packageSize(packageSize)
                .manifestJson(manifestJson)
                .status("pending")
                .build();
        version = versionRepository.save(version);

        Submission submission = Submission.builder()
                .versionId(version.getId())
                .type("new")
                .status("pending")
                .build();
        submissionRepository.save(submission);

        log.info("Skill submitted: skillId={}, version={}, submissionId={}", skillId, version.getId(), submission.getId());

        rocketMQTemplate.convertAndSend("store-skill-submitted",
                new SkillSubmittedMessage(submission.getId(), skillId, packageUrl));

        return skill;
    }

    @Transactional
    public SkillVersion publishNewVersion(Long developerId, String skillId, String version,
                                           String changelog, MultipartFile packageFile, String manifestJson) {
        Skill skill = skillRepository.findBySkillId(skillId)
                .orElseThrow(() -> new RuntimeException("Skill not found: " + skillId));

        if (!skill.getDeveloperId().equals(developerId)) {
            throw new RuntimeException("Not authorized to update this skill");
        }

        String packageUrl = storageService.uploadPackage(skillId, version, packageFile);
        long packageSize = packageFile.getSize();

        SkillVersion skillVersion = SkillVersion.builder()
                .skillId(skill.getId())
                .version(version)
                .changelog(changelog)
                .packageUrl(packageUrl)
                .packageSize(packageSize)
                .manifestJson(manifestJson)
                .status("pending")
                .build();
        skillVersion = versionRepository.save(skillVersion);

        Submission submission = Submission.builder()
                .versionId(skillVersion.getId())
                .type("update")
                .status("pending")
                .build();
        submissionRepository.save(submission);

        rocketMQTemplate.convertAndSend("store-skill-submitted",
                new SkillSubmittedMessage(submission.getId(), skillId, packageUrl));

        log.info("New version published: skillId={}, version={}", skillId, version);
        return skillVersion;
    }

    public List<Skill> listDeveloperSkills(Long developerId) {
        return skillRepository.findByDeveloperId(developerId);
    }

    public List<SkillVersion> listVersions(String skillId) {
        Skill skill = skillRepository.findBySkillId(skillId)
                .orElseThrow(() -> new RuntimeException("Skill not found: " + skillId));
        return versionRepository.findBySkillIdOrderByCreatedAtDesc(skill.getId());
    }

    @Transactional
    public Skill updateSkillInfo(Long developerId, String skillId, String name,
                                  String description, String tagline, Long categoryId) {
        Skill skill = skillRepository.findBySkillId(skillId)
                .orElseThrow(() -> new RuntimeException("Skill not found: " + skillId));

        if (!skill.getDeveloperId().equals(developerId)) {
            throw new RuntimeException("Not authorized to update this skill");
        }

        if (name != null) skill.setName(name);
        if (description != null) skill.setDescription(description);
        if (tagline != null) skill.setTagline(tagline);
        if (categoryId != null) skill.setCategoryId(categoryId);

        return skillRepository.save(skill);
    }

    @Transactional
    public void unpublishSkill(Long developerId, String skillId) {
        Skill skill = skillRepository.findBySkillId(skillId)
                .orElseThrow(() -> new RuntimeException("Skill not found: " + skillId));

        if (!skill.getDeveloperId().equals(developerId)) {
            throw new RuntimeException("Not authorized to unpublish this skill");
        }

        skill.setStatus("removed");
        skillRepository.save(skill);
        log.info("Skill unpublished: skillId={}", skillId);
    }

    @Transactional
    public void emergencyRecall(Long developerId, String skillId, String reason) {
        Skill skill = skillRepository.findBySkillId(skillId)
                .orElseThrow(() -> new RuntimeException("Skill not found: " + skillId));

        if (!skill.getDeveloperId().equals(developerId)) {
            throw new RuntimeException("Not authorized to recall this skill");
        }

        skill.setStatus("suspended");
        skillRepository.save(skill);

        log.warn("Emergency recall: skillId={}, reason={}", skillId, reason);
        rocketMQTemplate.convertAndSend("store-skill-recalled",
                new SkillRecalledMessage(skillId, reason));
    }

    public record SkillSubmittedMessage(Long submissionId, String skillId, String packageUrl) {}
    public record SkillRecalledMessage(String skillId, String reason) {}
}
