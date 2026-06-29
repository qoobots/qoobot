package com.qoobot.qoogear.standard.controller;

import com.qoobot.qoogear.common.dto.ApiResponse;
import com.qoobot.qoogear.common.dto.PageResponse;
import com.qoobot.qoogear.standard.domain.*;
import com.qoobot.qoogear.standard.service.StandardSpecService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/standard")
@RequiredArgsConstructor
public class StandardSpecController {

    private final StandardSpecService specService;

    // === Categories ===

    @GetMapping("/categories")
    public ApiResponse<List<StandardCategory>> listCategories() {
        return ApiResponse.success(specService.listCategories());
    }

    @GetMapping("/categories/roots")
    public ApiResponse<List<StandardCategory>> getRootCategories() {
        return ApiResponse.success(specService.getRootCategories());
    }

    @GetMapping("/categories/{id}/children")
    public ApiResponse<List<StandardCategory>> getSubCategories(@PathVariable Long id) {
        return ApiResponse.success(specService.getSubCategories(id));
    }

    @PostMapping("/categories")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<StandardCategory> createCategory(@RequestBody StandardCategory category) {
        return ApiResponse.success(specService.createCategory(category));
    }

    // === Specs ===

    @GetMapping("/specs")
    public ApiResponse<PageResponse<StandardSpec>> listSpecs(
            @RequestParam(required = false) Long categoryId,
            @RequestParam(required = false) String status,
            @PageableDefault(size = 20) Pageable pageable) {
        return ApiResponse.success(specService.listSpecs(categoryId, status, pageable));
    }

    @GetMapping("/specs/search")
    public ApiResponse<PageResponse<StandardSpec>> searchSpecs(
            @RequestParam String keyword,
            @PageableDefault(size = 20) Pageable pageable) {
        return ApiResponse.success(specService.searchSpecs(keyword, pageable));
    }

    @GetMapping("/specs/{id}")
    public ApiResponse<StandardSpec> getSpec(@PathVariable Long id) {
        return ApiResponse.success(specService.getSpec(id));
    }

    @GetMapping("/specs/{id}/versions")
    public ApiResponse<List<StandardSpec>> getVersions(@PathVariable Long id) {
        StandardSpec spec = specService.getSpec(id);
        return ApiResponse.success(specService.getSpecVersions(spec.getSpecNumber()));
    }

    @PostMapping("/specs")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<StandardSpec> createSpec(@RequestBody StandardSpec spec) {
        return ApiResponse.success(specService.createSpec(spec));
    }

    @PutMapping("/specs/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<StandardSpec> updateSpec(@PathVariable Long id, @RequestBody StandardSpec spec) {
        return ApiResponse.success(specService.updateSpec(id, spec));
    }

    @PostMapping("/specs/{id}/publish")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<StandardSpec> publishSpec(@PathVariable Long id) {
        return ApiResponse.success(specService.publishSpec(id));
    }

    @PostMapping("/specs/{id}/deprecate")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<StandardSpec> deprecateSpec(@PathVariable Long id) {
        return ApiResponse.success(specService.deprecateSpec(id));
    }

    // === Compatibility ===

    @GetMapping("/compatibility/{specId}")
    public ApiResponse<List<CompatibilityMatrix>> getCompatibility(@PathVariable Long specId) {
        return ApiResponse.success(specService.getCompatibilityForSpec(specId));
    }

    @PostMapping("/compatibility")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<CompatibilityMatrix> addCompatibility(@RequestBody CompatibilityMatrix matrix) {
        return ApiResponse.success(specService.addCompatibility(matrix));
    }

    // === Test Checklist ===

    @GetMapping("/specs/{id}/checklist")
    public ApiResponse<List<TestChecklist>> getChecklist(@PathVariable Long id) {
        return ApiResponse.success(specService.getChecklist(id));
    }

    @PostMapping("/specs/{id}/checklist")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<TestChecklist> addChecklistItem(@PathVariable Long id, @RequestBody TestChecklist item) {
        item.setStandardId(id);
        return ApiResponse.success(specService.addChecklistItem(item));
    }

    @DeleteMapping("/checklist/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<Void> removeChecklistItem(@PathVariable Long id) {
        specService.removeChecklistItem(id);
        return ApiResponse.success(null);
    }
}
