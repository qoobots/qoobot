package com.qoobot.qoogear.cert.controller;

import com.qoobot.qoogear.cert.domain.*;
import com.qoobot.qoogear.cert.service.*;
import com.qoobot.qoogear.common.dto.ApiResponse;
import com.qoobot.qoogear.common.dto.PageResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/cert")
@RequiredArgsConstructor
public class CertificationController {

    private final CertificationService certService;
    private final DeveloperService devService;

    // === Developer ===

    @PostMapping("/developers")
    public ApiResponse<Developer> register(@Valid @RequestBody Developer dev) {
        return ApiResponse.success(devService.register(dev));
    }

    @GetMapping("/developers/{id}")
    public ApiResponse<Developer> getDeveloper(@PathVariable Long id) {
        return ApiResponse.success(devService.getById(id));
    }

    @PostMapping("/developers/{id}/verify")
    public ApiResponse<Developer> verifyDeveloper(@PathVariable Long id, @RequestParam boolean approved) {
        return ApiResponse.success(devService.verify(id, approved));
    }

    // === Applications ===

    @PostMapping("/applications")
    public ApiResponse<CertApplication> createApplication(@Valid @RequestBody CertApplication app) {
        return ApiResponse.success(certService.createApplication(app));
    }

    @GetMapping("/applications")
    public ApiResponse<PageResponse<CertApplication>> listApplications(
            @RequestParam(required = false) Long developerId,
            @RequestParam(required = false) String status,
            @PageableDefault(size = 20) Pageable pageable) {
        return ApiResponse.success(certService.listApplications(developerId, status, pageable));
    }

    @GetMapping("/applications/{id}")
    public ApiResponse<CertApplication> getApplication(@PathVariable Long id) {
        return ApiResponse.success(
                certService.listApplications(null, null, null).getItems().stream()
                        .filter(a -> a.getId().equals(id)).findFirst()
                        .orElseThrow());
    }

    @PutMapping("/applications/{id}")
    public ApiResponse<CertApplication> updateApplication(@PathVariable Long id, @RequestBody CertApplication app) {
        // In production, use dedicated update method
        return ApiResponse.success(app);
    }

    @PostMapping("/applications/{id}/submit")
    public ApiResponse<CertApplication> submitApplication(@PathVariable Long id) {
        return ApiResponse.success(certService.submitApplication(id));
    }

    @PostMapping("/applications/{id}/review")
    public ApiResponse<CertApplication> reviewApplication(
            @PathVariable Long id,
            @RequestParam Long reviewerId,
            @RequestParam boolean approved,
            @RequestParam(required = false) String comment) {
        return ApiResponse.success(certService.reviewApplication(id, reviewerId, approved,
                comment != null ? comment : ""));
    }

    @PostMapping("/applications/{id}/assign-lab")
    public ApiResponse<CertApplication> assignLab(@PathVariable Long id, @RequestParam Long labId) {
        return ApiResponse.success(certService.assignLab(id, labId));
    }

    // === Certificates ===

    @PostMapping("/applications/{id}/issue")
    public ApiResponse<Certificate> issueCertificate(@PathVariable Long id) {
        return ApiResponse.success(certService.issueCertificate(id));
    }

    @PostMapping("/applications/{id}/revoke")
    public ApiResponse<Certificate> revokeCertificate(@PathVariable Long id, @RequestParam String reason) {
        return ApiResponse.success(certService.revokeCertificate(id, reason));
    }

    @GetMapping("/certificates")
    public ApiResponse<PageResponse<Certificate>> listCertificates(
            @RequestParam(required = false) Long developerId,
            @PageableDefault(size = 20) Pageable pageable) {
        return ApiResponse.success(certService.listCertificates(developerId, pageable));
    }

    @GetMapping("/certificates/{id}")
    public ApiResponse<Certificate> getCertificate(@PathVariable Long id) {
        return ApiResponse.success(certService.listCertificates(null, null).getItems().stream()
                .filter(c -> c.getId().equals(id)).findFirst()
                .orElseThrow());
    }

    @GetMapping("/certificates/verify/{certNumber}")
    public ApiResponse<Certificate> verifyCertificate(@PathVariable String certNumber) {
        return ApiResponse.success(certService.verifyCertificate(certNumber));
    }

    // === Test Reports ===

    @PostMapping("/applications/{id}/test-report")
    public ApiResponse<TestReport> submitTestReport(
            @PathVariable Long id,
            @RequestParam Long labId,
            @RequestParam String result,
            @RequestParam String summary) {
        return ApiResponse.success(certService.submitTestReport(id, labId, result, summary));
    }

    @GetMapping("/applications/{id}/test-reports")
    public ApiResponse<List<TestReport>> getTestReports(@PathVariable Long id) {
        return ApiResponse.success(certService.getTestReports(id));
    }

    // === Auth Chips ===

    @PostMapping("/certificates/{id}/chips")
    public ApiResponse<AuthChip> burnChip(
            @PathVariable Long id,
            @RequestParam String chipType,
            @RequestParam String batchNumber) {
        return ApiResponse.success(certService.burnChip(id, chipType, batchNumber));
    }

    @GetMapping("/certificates/{id}/chips")
    public ApiResponse<List<AuthChip>> listChips(@PathVariable Long id) {
        return ApiResponse.success(certService.listChips(id));
    }
}
