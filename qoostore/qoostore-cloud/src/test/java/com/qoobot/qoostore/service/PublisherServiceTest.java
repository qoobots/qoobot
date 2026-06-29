package com.qoobot.qoostore.service;

import com.qoobot.qoostore.entity.*;
import com.qoobot.qoostore.repository.*;
import org.apache.rocketmq.spring.core.RocketMQTemplate;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class PublisherServiceTest {

    @Mock private SkillRepository skillRepository;
    @Mock private SkillVersionRepository versionRepository;
    @Mock private SubmissionRepository submissionRepository;
    @Mock private DeveloperRepository developerRepository;
    @Mock private StorageService storageService;
    @Mock private RocketMQTemplate rocketMQTemplate;

    @InjectMocks
    private PublisherService publisherService;

    private Developer testDeveloper;

    @BeforeEach
    void setUp() {
        testDeveloper = Developer.builder()
                .id(100L)
                .userId(java.util.UUID.randomUUID())
                .username("testdev")
                .email("dev@test.com")
                .build();
    }

    @Test
    void submitSkill_shouldCreateSkillAndVersion() {
        MultipartFile mockFile = mock(MultipartFile.class);
        when(mockFile.getSize()).thenReturn(1024L);

        when(developerRepository.findById(100L)).thenReturn(Optional.of(testDeveloper));
        when(skillRepository.findBySkillId("com.test.newskill")).thenReturn(Optional.empty());
        when(storageService.uploadPackage(anyString(), anyString(), any())).thenReturn("s3://test");
        when(skillRepository.save(any(Skill.class))).thenAnswer(inv -> {
            Skill s = inv.getArgument(0);
            s.setId(1L);
            return s;
        });
        when(versionRepository.save(any(SkillVersion.class))).thenAnswer(inv -> {
            SkillVersion v = inv.getArgument(0);
            v.setId(1L);
            return v;
        });
        when(submissionRepository.save(any(Submission.class))).thenAnswer(inv -> inv.getArgument(0));

        Skill result = publisherService.submitSkill(
                100L, "com.test.newskill", "新技能", "描述", 1L, "简介", mockFile, "{}");

        assertThat(result).isNotNull();
        assertThat(result.getSkillId()).isEqualTo("com.test.newskill");
        assertThat(result.getStatus()).isEqualTo("draft");

        verify(rocketMQTemplate).convertAndSend(eq("store-skill-submitted"), any());
    }

    @Test
    void submitSkill_shouldFailWhenDeveloperNotFound() {
        when(developerRepository.findById(999L)).thenReturn(Optional.empty());

        MultipartFile mockFile = mock(MultipartFile.class);
        assertThatThrownBy(() -> publisherService.submitSkill(
                999L, "com.test.fail", "失败", "描述", 1L, "简介", mockFile, "{}"))
                .isInstanceOf(RuntimeException.class)
                .hasMessageContaining("Developer not found");
    }

    @Test
    void submitSkill_shouldFailWhenSkillIdExists() {
        when(developerRepository.findById(100L)).thenReturn(Optional.of(testDeveloper));
        when(skillRepository.findBySkillId("com.test.duplicate"))
                .thenReturn(Optional.of(Skill.builder().build()));

        MultipartFile mockFile = mock(MultipartFile.class);
        assertThatThrownBy(() -> publisherService.submitSkill(
                100L, "com.test.duplicate", "重复", "描述", 1L, "简介", mockFile, "{}"))
                .isInstanceOf(RuntimeException.class)
                .hasMessageContaining("already exists");
    }

    @Test
    void listDeveloperSkills_shouldReturnSkills() {
        Skill skill = Skill.builder().skillId("com.test.skill1").developerId(100L).build();
        when(skillRepository.findByDeveloperId(100L)).thenReturn(List.of(skill));

        List<Skill> result = publisherService.listDeveloperSkills(100L);

        assertThat(result).hasSize(1);
    }

    @Test
    void unpublishSkill_shouldSetStatusRemoved() {
        Skill skill = Skill.builder()
                .skillId("com.test.skill1")
                .developerId(100L)
                .status("published")
                .build();
        when(skillRepository.findBySkillId("com.test.skill1")).thenReturn(Optional.of(skill));
        when(skillRepository.save(any(Skill.class))).thenReturn(skill);

        publisherService.unpublishSkill(100L, "com.test.skill1");

        assertThat(skill.getStatus()).isEqualTo("removed");
    }

    @Test
    void emergencyRecall_shouldSendRocketMQMessage() {
        Skill skill = Skill.builder()
                .skillId("com.test.skill1")
                .developerId(100L)
                .status("published")
                .build();
        when(skillRepository.findBySkillId("com.test.skill1")).thenReturn(Optional.of(skill));
        when(skillRepository.save(any(Skill.class))).thenReturn(skill);

        publisherService.emergencyRecall(100L, "com.test.skill1", "安全漏洞");

        assertThat(skill.getStatus()).isEqualTo("suspended");
        verify(rocketMQTemplate).convertAndSend(eq("store-skill-recalled"), any());
    }
}
