package com.qoobot.qoogear.security.controller;

import com.qoobot.qoogear.common.dto.ApiResponse;
import com.qoobot.qoogear.security.domain.SecurityAudit;
import com.qoobot.qoogear.security.service.SecurityAuditService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/security")
@RequiredArgsConstructor
public class SecurityAuditController {

    private final SecurityAuditService auditService;

    @PostMapping("/risk-assessment")
    public ApiResponse<SecurityAudit> createAudit(@RequestBody SecurityAudit audit) {
        return ApiResponse.success(auditService.createAudit(audit));
    }

    @GetMapping("/risk-assessment/{id}")
    public ApiResponse<SecurityAudit> getAudit(@PathVariable Long id) {
        return ApiResponse.success(auditService.getAudit(id));
    }

    @GetMapping("/risk-assessment/application/{appId}")
    public ApiResponse<SecurityAudit> getByApplication(@PathVariable Long appId) {
        return ApiResponse.success(auditService.getAuditByApplication(appId));
    }

    @PutMapping("/risk-assessment/{id}")
    public ApiResponse<SecurityAudit> updateAudit(
            @PathVariable Long id,
            @RequestParam String riskLevel,
            @RequestParam String findings,
            @RequestParam String recommendation) {
        return ApiResponse.success(auditService.completeAudit(id, riskLevel, findings, recommendation));
    }

    @PutMapping("/risk-assessment/{id}/fmea")
    public ApiResponse<SecurityAudit> updateFmea(@PathVariable Long id, @RequestBody String fmeaJson) {
        return ApiResponse.success(auditService.updateFmea(id, fmeaJson));
    }

    @GetMapping("/risk-level-counts")
    public ApiResponse<Long> countByRiskLevel(@RequestParam String riskLevel) {
        return ApiResponse.success(auditService.countByRiskLevel(riskLevel));
    }
}
