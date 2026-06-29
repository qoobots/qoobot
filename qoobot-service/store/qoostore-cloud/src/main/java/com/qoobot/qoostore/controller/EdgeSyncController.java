package com.qoobot.qoostore.controller;

import com.qoobot.qoostore.dto.response.ApiResponse;
import com.qoobot.qoostore.entity.DeviceSkill;
import com.qoobot.qoostore.service.EdgeSyncService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/edge")
@RequiredArgsConstructor
@Tag(name = "端侧同步", description = "技能安装/更新/卸载/下载")
public class EdgeSyncController {

    private final EdgeSyncService edgeSyncService;

    @GetMapping("/robot/{deviceId}/skills")
    @Operation(summary = "设备已安装技能")
    public ApiResponse<List<DeviceSkill>> getDeviceSkills(@PathVariable String deviceId) {
        return ApiResponse.success(edgeSyncService.getDeviceSkills(deviceId));
    }

    @PostMapping("/robot/{deviceId}/skills/{skillId}/install")
    @Operation(summary = "安装技能")
    public ApiResponse<DeviceSkill> installSkill(
            @PathVariable String deviceId,
            @PathVariable String skillId,
            @RequestParam String licenseKey) {
        return ApiResponse.success(edgeSyncService.installSkill(deviceId, skillId, licenseKey));
    }

    @PostMapping("/robot/{deviceId}/skills/{skillId}/update")
    @Operation(summary = "更新技能")
    public ApiResponse<DeviceSkill> updateSkill(
            @PathVariable String deviceId,
            @PathVariable String skillId) {
        return ApiResponse.success(edgeSyncService.updateSkill(deviceId, skillId));
    }

    @PostMapping("/robot/{deviceId}/skills/{skillId}/uninstall")
    @Operation(summary = "卸载技能")
    public ApiResponse<Void> uninstallSkill(
            @PathVariable String deviceId,
            @PathVariable String skillId) {
        edgeSyncService.uninstallSkill(deviceId, skillId);
        return ApiResponse.success("Uninstalled", null);
    }

    @GetMapping("/skills/{skillId}/download")
    @Operation(summary = "获取下载链接")
    public ApiResponse<Map<String, String>> getDownloadUrl(
            @PathVariable String skillId,
            @RequestParam String deviceId) {
        String url = edgeSyncService.getDownloadUrl(skillId, deviceId);
        return ApiResponse.success(Map.of("downloadUrl", url));
    }
}
