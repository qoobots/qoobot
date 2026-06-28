package com.qoobot.qoostore.controller;

import com.qoobot.qoostore.dto.response.*;
import com.qoobot.qoostore.entity.Category;
import com.qoobot.qoostore.service.StorefrontService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/store")
@RequiredArgsConstructor
@Tag(name = "技能商店", description = "技能浏览/搜索/推荐/排行")
public class StorefrontController {

    private final StorefrontService storefrontService;

    @GetMapping("/skills")
    @Operation(summary = "技能列表")
    public ApiResponse<SkillListResponse> listSkills(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(defaultValue = "newest") String sortBy) {
        return ApiResponse.success(storefrontService.listSkills(page, size, sortBy));
    }

    @GetMapping("/skills/{skillId}")
    @Operation(summary = "技能详情")
    public ApiResponse<SkillResponse> getSkill(@PathVariable String skillId) {
        return ApiResponse.success(storefrontService.getSkillDetail(skillId));
    }

    @GetMapping("/skills/{skillId}/reviews")
    @Operation(summary = "技能评价列表")
    public ApiResponse<Page<ReviewResponse>> getReviews(
            @PathVariable String skillId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.success(storefrontService.getSkillReviews(
                storefrontService.getSkillDetail(skillId).getId(), page, size));
    }

    @GetMapping("/search")
    @Operation(summary = "技能搜索")
    public ApiResponse<SkillListResponse> search(
            @RequestParam String q,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.success(storefrontService.searchSkills(q, page, size));
    }

    @GetMapping("/categories")
    @Operation(summary = "分类列表")
    public ApiResponse<List<Category>> listCategories() {
        return ApiResponse.success(storefrontService.listCategories());
    }

    @GetMapping("/categories/{slug}/skills")
    @Operation(summary = "分类下技能")
    public ApiResponse<SkillListResponse> listByCategory(
            @PathVariable String slug,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.success(storefrontService.listSkillsByCategory(slug, page, size));
    }

    @GetMapping("/featured")
    @Operation(summary = "精选推荐")
    public ApiResponse<List<SkillResponse>> getFeatured() {
        return ApiResponse.success(storefrontService.getFeaturedSkills());
    }

    @GetMapping("/rankings")
    @Operation(summary = "排行榜")
    public ApiResponse<SkillListResponse> getRankings(
            @RequestParam(defaultValue = "downloads") String type,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.success(storefrontService.getRankings(type, page, size));
    }
}
