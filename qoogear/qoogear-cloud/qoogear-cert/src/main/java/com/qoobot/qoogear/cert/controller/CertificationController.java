package com.qoobot.qoogear.cert.controller;

import com.qoobot.qoogear.cert.domain.*;
import com.qoobot.qoogear.cert.repository.CertApplicationRepository;
import com.qoobot.qoogear.cert.repository.CertificateRepository;
import com.qoobot.qoogear.cert.service.*;
import com.qoobot.qoogear.common.dto.ApiResponse;
import com.qoobot.qoogear.common.dto.PageResponse;
import com.qoobot.qoogear.common.security.SecurityUtils;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.time.ZonedDateTime;
import java.util.List;
import java.util.Map;

/**
 * MFQ Certification REST API.
 *
 * Role-based access:
 *   GET  /public/**  — anonymous access (public catalog)
 *   /**               — authenticated (DEVELOPER / ADMIN)
 *   /admin/**         — ADMIN only
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/cert")
@RequiredArgsConstructor
public class CertificationController {

    private final CertificationService certService;
    private final DeveloperService devService;
    private final SecurityUtils securityUtils;
    private final CertApplicationRepository appRepo;
    private final CertificateRepository certRepo;

    // === Public Endpoints ===

    @GetMapping("/public/certificates")
    public ApiResponse<PageResponse<Certificate>> publicCertificates(
            @PageableDefault(size = 20) Pageable pageable) {
        return ApiResponse.success(certService.listCertificates(null, pageable));
    }

    @GetMapping("/public/certificates/verify/{certNumber}")
    public ApiResponse<Certificate> publicVerifyCertificate(@PathVariable String certNumber) {
        return ApiResponse.success(certService.verifyCertificate(certNumber));
    }

    // === Developer Endpoints ===

    @PostMapping("/developers")
    @PreAuthorize("hasRole('DEVELOPER') or hasRole('ADMIN')")
    public ApiResponse<Developer> register(@Valid @RequestBody Developer dev) {
        return ApiResponse.success(devService.register(dev));
    }

    @GetMapping("/developers/{id}")
    @PreAuthorize("hasRole('DEVELOPER') or hasRole('ADMIN')")
    public ApiResponse<Developer> getDeveloper(@PathVariable Long id) {
        return ApiResponse.success(devService.getById(id));
    }

    @PostMapping("/developers/{id}/verify")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<Developer> verifyDeveloper(@PathVariable Long id, @RequestParam boolean approved) {
        return ApiResponse.success(devService.verify(id, approved));
    }

    // === Application Endpoints ===

    @PostMapping("/applications")
    @PreAuthorize("hasRole('DEVELOPER') or hasRole('ADMIN')")
    public ApiResponse<CertApplication> createApplication(@Valid @RequestBody CertApplication app) {
        return ApiResponse.success(certService.createApplication(app));
    }

    @GetMapping("/applications")
    @PreAuthorize("hasRole('DEVELOPER') or hasRole('ADMIN')")
    public ApiResponse<PageResponse<CertApplication>> listApplications(
            @RequestParam(required = false) Long developerId,
            @RequestParam(required = false) String status,
            @PageableDefault(size = 20) Pageable pageable) {
        return ApiResponse.success(certService.listApplications(developerId, status, pageable));
    }

    @GetMapping("/applications/{id}")
    @PreAuthorize("hasRole('DEVELOPER') or hasRole('ADMIN')")
    public ApiResponse<CertApplication> getApplication(@PathVariable Long id) {
        return ApiResponse.success(certService.getApplication(id));
    }

    @PutMapping("/applications/{id}")
    @PreAuthorize("hasRole('DEVELOPER') or hasRole('ADMIN')")
    public ApiResponse<CertApplication> updateApplication(@PathVariable Long id, @RequestBody CertApplication app) {
        return ApiResponse.success(certService.updateApplication(id, app));
    }

    @PostMapping("/applications/{id}/submit")
    @PreAuthorize("hasRole('DEVELOPER') or hasRole('ADMIN')")
    public ApiResponse<CertApplication> submitApplication(@PathVariable Long id) {
        return ApiResponse.success(certService.submitApplication(id));
    }

    @PostMapping("/applications/{id}/review")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<CertApplication> reviewApplication(
            @PathVariable Long id,
            @RequestParam Long reviewerId,
            @RequestParam boolean approved,
            @RequestParam(required = false) String comment) {
        return ApiResponse.success(certService.reviewApplication(id, reviewerId, approved,
                comment != null ? comment : ""));
    }

    @PostMapping("/applications/{id}/assign-lab")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<CertApplication> assignLab(@PathVariable Long id, @RequestParam Long labId) {
        return ApiResponse.success(certService.assignLab(id, labId));
    }

    // === Certificate Admin Endpoints ===

    @PostMapping("/applications/{id}/issue")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<Certificate> issueCertificate(@PathVariable Long id) {
        return ApiResponse.success(certService.issueCertificate(id));
    }

    @PostMapping("/applications/{id}/revoke")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<Certificate> revokeCertificate(@PathVariable Long id, @RequestParam String reason) {
        return ApiResponse.success(certService.revokeCertificate(id, reason));
    }

    @GetMapping("/certificates")
    @PreAuthorize("hasRole('DEVELOPER') or hasRole('ADMIN')")
    public ApiResponse<PageResponse<Certificate>> listCertificates(
            @RequestParam(required = false) Long developerId,
            @PageableDefault(size = 20) Pageable pageable) {
        return ApiResponse.success(certService.listCertificates(developerId, pageable));
    }

    @GetMapping("/certificates/{id}")
    @PreAuthorize("hasRole('DEVELOPER') or hasRole('ADMIN')")
    public ApiResponse<Certificate> getCertificate(@PathVariable Long id) {
        Certificate cert = certRepo.findById(id)
                .orElseThrow(() -> com.qoobot.qoogear.common.exception.QooGearException.notFound("Certificate", id));
        return ApiResponse.success(cert);
    }

    @GetMapping("/certificates/verify/{certNumber}")
    @PreAuthorize("hasRole('DEVELOPER') or hasRole('ADMIN')")
    public ApiResponse<Certificate> verifyCertificate(@PathVariable String certNumber) {
        return ApiResponse.success(certService.verifyCertificate(certNumber));
    }

    // === Test Reports ===

    @PostMapping("/applications/{id}/test-report")
    @PreAuthorize("hasRole('LAB_TECHNICIAN') or hasRole('ADMIN')")
    public ApiResponse<TestReport> submitTestReport(
            @PathVariable Long id,
            @RequestParam Long labId,
            @RequestParam String result,
            @RequestParam String summary) {
        return ApiResponse.success(certService.submitTestReport(id, labId, result, summary));
    }

    @GetMapping("/applications/{id}/test-reports")
    @PreAuthorize("hasRole('DEVELOPER') or hasRole('ADMIN') or hasRole('LAB_TECHNICIAN')")
    public ApiResponse<List<TestReport>> getTestReports(@PathVariable Long id) {
        return ApiResponse.success(certService.getTestReports(id));
    }

    // === Auth Chips ===

    @PostMapping("/certificates/{id}/chips")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<AuthChip> burnChip(
            @PathVariable Long id,
            @RequestParam String chipType,
            @RequestParam String batchNumber) {
        return ApiResponse.success(certService.burnChip(id, chipType, batchNumber));
    }

    @GetMapping("/certificates/{id}/chips")
    @PreAuthorize("hasRole('DEVELOPER') or hasRole('ADMIN')")
    public ApiResponse<List<AuthChip>> listChips(@PathVariable Long id) {
        return ApiResponse.success(certService.listChips(id));
    }

    // === Admin Dashboard ===

    @GetMapping("/admin/dashboard")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<Map<String, Object>> adminDashboard() {
        var dashboard = Map.<String, Object>of(
                "totalApplications", appRepo.count(),
                "totalCertificates", certRepo.count(),
                "expiringSoon", certService.findExpiringSoon(30).size()
        );
        return ApiResponse.success(dashboard);
    }
}
