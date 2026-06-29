package com.qoobot.qoogear.security.controller;

import com.qoobot.qoogear.common.dto.ApiResponse;
import com.qoobot.qoogear.security.domain.SecurityAudit;
import com.qoobot.qoogear.security.service.SecurityAuditService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/security")
@RequiredArgsConstructor
public class SecurityAuditController {

    private final SecurityAuditService auditService;

    @PostMapping("/risk-assessment")
    @PreAuthorize("hasRole('ADMIN') or hasRole('SECURITY_AUDITOR')")
    public ApiResponse<SecurityAudit> createAudit(@RequestBody SecurityAudit audit) {
        return ApiResponse.success(auditService.createAudit(audit));
    }

    @GetMapping("/risk-assessment/{id}")
    @PreAuthorize("hasRole('ADMIN') or hasRole('SECURITY_AUDITOR')")
    public ApiResponse<SecurityAudit> getAudit(@PathVariable Long id) {
        return ApiResponse.success(auditService.getAudit(id));
    }

    @GetMapping("/risk-assessment/application/{appId}")
    @PreAuthorize("hasRole('ADMIN') or hasRole('SECURITY_AUDITOR')")
    public ApiResponse<SecurityAudit> getByApplication(@PathVariable Long appId) {
        return ApiResponse.success(auditService.getAuditByApplication(appId));
    }

    @PutMapping("/risk-assessment/{id}")
    @PreAuthorize("hasRole('ADMIN') or hasRole('SECURITY_AUDITOR')")
    public ApiResponse<SecurityAudit> updateAudit(
            @PathVariable Long id,
            @RequestParam String riskLevel,
            @RequestParam String findings,
            @RequestParam String recommendation) {
        return ApiResponse.success(auditService.completeAudit(id, riskLevel, findings, recommendation));
    }

    @PutMapping("/risk-assessment/{id}/fmea")
    @PreAuthorize("hasRole('ADMIN') or hasRole('SECURITY_AUDITOR')")
    public ApiResponse<SecurityAudit> updateFmea(@PathVariable Long id, @RequestBody String fmeaJson) {
        return ApiResponse.success(auditService.updateFmea(id, fmeaJson));
    }

    @GetMapping("/risk-level-counts")
    @PreAuthorize("hasRole('ADMIN') or hasRole('SECURITY_AUDITOR')")
    public ApiResponse<Long> countByRiskLevel(@RequestParam String riskLevel) {
        return ApiResponse.success(auditService.countByRiskLevel(riskLevel));
    }
}
