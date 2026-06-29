package com.qoobot.qoogear.developer.controller;

import com.qoobot.qoogear.common.dto.ApiResponse;
import com.qoobot.qoogear.common.dto.PageResponse;
import com.qoobot.qoogear.developer.domain.*;
import com.qoobot.qoogear.developer.service.*;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/developer")
@RequiredArgsConstructor
public class DeveloperPortalController {

    private final ReferenceDesignService designService;
    private final SdkService sdkService;
    private final TestKitService kitService;

    // === Reference Designs ===

    @GetMapping("/references")
    public ApiResponse<PageResponse<ReferenceDesign>> listDesigns(
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String keyword,
            @PageableDefault(size = 20) Pageable pageable) {
        return ApiResponse.success(designService.listDesigns(category, keyword, pageable));
    }

    @GetMapping("/references/{id}")
    public ApiResponse<ReferenceDesign> getDesign(@PathVariable Long id) {
        return ApiResponse.success(designService.getDesign(id));
    }

    @PostMapping("/references")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<ReferenceDesign> createDesign(@RequestBody ReferenceDesign design) {
        return ApiResponse.success(designService.createDesign(design));
    }

    @PostMapping("/references/{id}/download")
    @PreAuthorize("hasRole('DEVELOPER') or hasRole('ADMIN')")
    public ApiResponse<Void> downloadDesign(@PathVariable Long id) {
        designService.incrementDownloads(id);
        return ApiResponse.success("Download recorded", null);
    }

    // === SDK ===

    @GetMapping("/sdk")
    public ApiResponse<List<SdkRelease>> listSdks(@RequestParam(defaultValue = "python") String platform) {
        return ApiResponse.success(sdkService.listReleases(platform));
    }

    @GetMapping("/sdk/{platform}/latest")
    public ApiResponse<SdkRelease> getLatestSdk(@PathVariable String platform) {
        return ApiResponse.success(sdkService.getLatest(platform));
    }

    @GetMapping("/sdk/{id}")
    public ApiResponse<SdkRelease> getSdkRelease(@PathVariable Long id) {
        return ApiResponse.success(sdkService.getRelease(id));
    }

    @PostMapping("/sdk")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<SdkRelease> publishSdk(@RequestBody SdkRelease release) {
        return ApiResponse.success(sdkService.publishRelease(release));
    }

    // === Test Kits ===

    @GetMapping("/test-kits")
    public ApiResponse<List<TestKit>> listAvailableKits() {
        return ApiResponse.success(kitService.listAvailable());
    }

    @GetMapping("/test-kits/type/{type}")
    public ApiResponse<List<TestKit>> listKitsByType(@PathVariable String type) {
        return ApiResponse.success(kitService.listByType(type));
    }

    @GetMapping("/test-kits/{id}")
    public ApiResponse<TestKit> getKit(@PathVariable Long id) {
        return ApiResponse.success(kitService.getKit(id));
    }

    @PostMapping("/test-kits")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<TestKit> createKit(@RequestBody TestKit kit) {
        return ApiResponse.success(kitService.createKit(kit));
    }

    @PutMapping("/test-kits/{id}/stock")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<TestKit> updateStock(@PathVariable Long id, @RequestParam int stock) {
        return ApiResponse.success(kitService.updateStock(id, stock));
    }
}
