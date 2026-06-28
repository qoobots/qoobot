package com.qoobot.qoostore.controller;

import com.qoobot.qoostore.dto.response.ApiResponse;
import com.qoobot.qoostore.entity.Skill;
import com.qoobot.qoostore.entity.SkillVersion;
import com.qoobot.qoostore.service.PublisherService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/api/v1/publisher")
@RequiredArgsConstructor
@Tag(name = "技能发布", description = "技能上传/版本管理/审核追踪")
public class PublisherController {

    private final PublisherService publisherService;

    @PostMapping("/skills")
    @Operation(summary = "提交新技能")
    public ApiResponse<Skill> submitSkill(
            @RequestParam Long developerId,
            @RequestParam String skillId,
            @RequestParam String name,
            @RequestParam String description,
            @RequestParam Long categoryId,
            @RequestParam(required = false) String tagline,
            @RequestParam MultipartFile packageFile,
            @RequestParam String manifestJson) {
        return ApiResponse.success(publisherService.submitSkill(
                developerId, skillId, name, description, categoryId, tagline, packageFile, manifestJson));
    }

    @GetMapping("/skills")
    @Operation(summary = "我的技能列表")
    public ApiResponse<List<Skill>> listMySkills(@RequestParam Long developerId) {
        return ApiResponse.success(publisherService.listDeveloperSkills(developerId));
    }

    @GetMapping("/skills/{skillId}")
    @Operation(summary = "我的技能详情")
    public ApiResponse<Skill> getMySkill(@RequestParam Long developerId, @PathVariable String skillId) {
        return ApiResponse.success(publisherService.listDeveloperSkills(developerId)
                .stream().filter(s -> s.getSkillId().equals(skillId)).findFirst()
                .orElseThrow(() -> new RuntimeException("Skill not found")));
    }

    @PutMapping("/skills/{skillId}")
    @Operation(summary = "更新技能信息")
    public ApiResponse<Skill> updateSkill(
            @RequestParam Long developerId,
            @PathVariable String skillId,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String description,
            @RequestParam(required = false) String tagline,
            @RequestParam(required = false) Long categoryId) {
        return ApiResponse.success(publisherService.updateSkillInfo(
                developerId, skillId, name, description, tagline, categoryId));
    }

    @PostMapping("/skills/{skillId}/versions")
    @Operation(summary = "发布新版本")
    public ApiResponse<SkillVersion> publishVersion(
            @RequestParam Long developerId,
            @PathVariable String skillId,
            @RequestParam String version,
            @RequestParam(required = false) String changelog,
            @RequestParam MultipartFile packageFile,
            @RequestParam String manifestJson) {
        return ApiResponse.success(publisherService.publishNewVersion(
                developerId, skillId, version, changelog, packageFile, manifestJson));
    }

    @GetMapping("/skills/{skillId}/versions")
    @Operation(summary = "版本列表")
    public ApiResponse<List<SkillVersion>> listVersions(@PathVariable String skillId) {
        return ApiResponse.success(publisherService.listVersions(skillId));
    }

    @DeleteMapping("/skills/{skillId}")
    @Operation(summary = "下架技能")
    public ApiResponse<Void> unpublishSkill(
            @RequestParam Long developerId, @PathVariable String skillId) {
        publisherService.unpublishSkill(developerId, skillId);
        return ApiResponse.success("Skill unpublished", null);
    }

    @PostMapping("/skills/{skillId}/recall")
    @Operation(summary = "紧急召回")
    public ApiResponse<Void> emergencyRecall(
            @RequestParam Long developerId,
            @PathVariable String skillId,
            @RequestParam String reason) {
        publisherService.emergencyRecall(developerId, skillId, reason);
        return ApiResponse.success("Emergency recall initiated", null);
    }
}
