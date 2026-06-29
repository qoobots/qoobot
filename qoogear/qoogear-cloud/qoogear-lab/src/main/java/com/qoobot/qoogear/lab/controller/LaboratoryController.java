package com.qoobot.qoogear.lab.controller;

import com.qoobot.qoogear.common.dto.ApiResponse;
import com.qoobot.qoogear.lab.domain.*;
import com.qoobot.qoogear.lab.service.LaboratoryService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/lab")
@RequiredArgsConstructor
public class LaboratoryController {

    private final LaboratoryService labService;

    // === Laboratories ===

    @GetMapping("/laboratories")
    public ApiResponse<List<Laboratory>> listActive() {
        return ApiResponse.success(labService.listActive());
    }

    @GetMapping("/laboratories/country/{country}")
    public ApiResponse<List<Laboratory>> listByCountry(@PathVariable String country) {
        return ApiResponse.success(labService.listByCountry(country));
    }

    @GetMapping("/laboratories/{id}")
    public ApiResponse<Laboratory> getLab(@PathVariable Long id) {
        return ApiResponse.success(labService.getLab(id));
    }

    @PostMapping("/laboratories")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<Laboratory> registerLab(@RequestBody Laboratory lab) {
        return ApiResponse.success(labService.registerLab(lab));
    }

    @PutMapping("/laboratories/{id}/status")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<Laboratory> updateStatus(@PathVariable Long id, @RequestParam String status) {
        return ApiResponse.success(labService.updateStatus(id, status));
    }

    // === Equipment ===

    @GetMapping("/laboratories/{id}/equipment")
    @PreAuthorize("hasRole('LAB_TECHNICIAN') or hasRole('ADMIN')")
    public ApiResponse<List<LabEquipment>> getEquipment(@PathVariable Long id) {
        return ApiResponse.success(labService.getEquipment(id));
    }

    @PostMapping("/laboratories/{id}/equipment")
    @PreAuthorize("hasRole('LAB_TECHNICIAN') or hasRole('ADMIN')")
    public ApiResponse<LabEquipment> addEquipment(@PathVariable Long id, @RequestBody LabEquipment equipment) {
        equipment.setLaboratoryId(id);
        return ApiResponse.success(labService.addEquipment(equipment));
    }

    @PostMapping("/equipment/{id}/calibrate")
    @PreAuthorize("hasRole('LAB_TECHNICIAN') or hasRole('ADMIN')")
    public ApiResponse<LabEquipment> calibrate(@PathVariable Long id) {
        return ApiResponse.success(labService.calibrateEquipment(id));
    }

    @GetMapping("/equipment/needs-calibration")
    @PreAuthorize("hasRole('LAB_TECHNICIAN') or hasRole('ADMIN')")
    public ApiResponse<List<LabEquipment>> needsCalibration(@RequestParam(defaultValue = "30") int days) {
        return ApiResponse.success(labService.findNeedingCalibration(days));
    }
}
