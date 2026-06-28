package com.qoobot.qoogear.cert.service;

import com.qoobot.qoogear.cert.domain.*;
import com.qoobot.qoogear.cert.repository.*;
import com.qoobot.qoogear.common.dto.PageResponse;
import com.qoobot.qoogear.common.enums.ApplicationStatus;
import com.qoobot.qoogear.common.exception.QooGearException;
import com.qoobot.qoogear.common.util.CertNumberGenerator;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.ZonedDateTime;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class CertificationService {

    private final CertApplicationRepository appRepo;
    private final CertificateRepository certRepo;
    private final DeveloperRepository devRepo;
    private final TestReportRepository testReportRepo;
    private final AuthChipRepository chipRepo;

    // === Application Management ===

    @Transactional
    public CertApplication createApplication(CertApplication app) {
        Developer dev = devRepo.findById(app.getDeveloperId())
                .orElseThrow(() -> QooGearException.notFound("Developer", app.getDeveloperId()));
        if (!"verified".equals(dev.getVerificationStatus())) {
            throw QooGearException.badRequest("Developer not verified");
        }
        app.setStatus(ApplicationStatus.DRAFT.name().toLowerCase());
        return appRepo.save(app);
    }

    @Transactional
    public CertApplication submitApplication(Long appId) {
        CertApplication app = appRepo.findById(appId)
                .orElseThrow(() -> QooGearException.notFound("CertApplication", appId));
        if (!ApplicationStatus.DRAFT.name().toLowerCase().equals(app.getStatus())) {
            throw QooGearException.badRequest("Only draft applications can be submitted");
        }
        app.setStatus(ApplicationStatus.SUBMITTED.name().toLowerCase());
        app.setSubmittedAt(ZonedDateTime.now());
        return appRepo.save(app);
    }

    @Transactional
    public CertApplication reviewApplication(Long appId, Long reviewerId, boolean approved, String comment) {
        CertApplication app = appRepo.findById(appId)
                .orElseThrow(() -> QooGearException.notFound("CertApplication", appId));

        String currentStatus = app.getStatus();
        if (approved) {
            if (ApplicationStatus.SUBMITTED.name().toLowerCase().equals(currentStatus)) {
                app.setStatus(ApplicationStatus.COMPLIANCE_CHECK.name().toLowerCase());
            } else if (ApplicationStatus.COMPLIANCE_CHECK.name().toLowerCase().equals(currentStatus)) {
                app.setStatus(ApplicationStatus.REVIEWING.name().toLowerCase());
            }
        } else {
            app.setStatus(ApplicationStatus.REJECTED.name().toLowerCase());
            app.setRejectionReason(comment);
        }

        app.setReviewedBy(reviewerId);
        app.setReviewComment(comment);
        app.setReviewedAt(ZonedDateTime.now());
        return appRepo.save(app);
    }

    @Transactional
    public CertApplication assignLab(Long appId, Long labId) {
        CertApplication app = appRepo.findById(appId)
                .orElseThrow(() -> QooGearException.notFound("CertApplication", appId));
        app.setAssignedLabId(labId);
        app.setAssignedAt(ZonedDateTime.now());
        app.setStatus(ApplicationStatus.ASSIGNED.name().toLowerCase());
        return appRepo.save(app);
    }

    public PageResponse<CertApplication> listApplications(Long developerId, String status, Pageable pageable) {
        Page<CertApplication> page;
        if (developerId != null) {
            page = appRepo.findByDeveloperId(developerId, pageable);
        } else if (status != null) {
            page = appRepo.findByStatus(status, pageable);
        } else {
            page = appRepo.findAll(pageable);
        }
        return PageResponse.of(page.getContent(), page.getTotalElements(),
                page.getNumber(), page.getSize());
    }

    // === Certificate Management ===

    @Transactional
    public Certificate issueCertificate(Long appId) {
        CertApplication app = appRepo.findById(appId)
                .orElseThrow(() -> QooGearException.notFound("CertApplication", appId));

        // Verify all conditions met
        long testReports = testReportRepo.countByApplicationId(appId);
        if (testReports == 0) {
            throw QooGearException.badRequest("Test reports required before issuing certificate");
        }

        Certificate cert = new Certificate();
        cert.setApplicationId(appId);
        cert.setCertNumber(CertNumberGenerator.generateForLevel(app.getCertLevel()));
        cert.setCertLevel(app.getCertLevel());
        cert.setDeveloperId(app.getDeveloperId());
        cert.setProductName(app.getProductName());
        cert.setProductModel(app.getProductModel());
        cert.setProductCategory(app.getProductCategory());
        cert.setIssuedAt(ZonedDateTime.now());
        cert.setExpiresAt(ZonedDateTime.now().plusYears(2));

        Certificate saved = certRepo.save(cert);

        app.setStatus(ApplicationStatus.APPROVED.name().toLowerCase());
        app.setApprovedAt(ZonedDateTime.now());
        appRepo.save(app);

        log.info("Certificate issued: {} for application {}", saved.getCertNumber(), appId);
        return saved;
    }

    @Transactional
    public Certificate revokeCertificate(Long certId, String reason) {
        Certificate cert = certRepo.findById(certId)
                .orElseThrow(() -> QooGearException.notFound("Certificate", certId));
        cert.setRevokedAt(ZonedDateTime.now());
        cert.setRevokeReason(reason);
        log.warn("Certificate revoked: {} - {}", cert.getCertNumber(), reason);
        return certRepo.save(cert);
    }

    public Certificate verifyCertificate(String certNumber) {
        Certificate cert = certRepo.findByCertNumber(certNumber)
                .orElseThrow(() -> QooGearException.notFound("Certificate", certNumber));
        if (!cert.isActive()) {
            throw QooGearException.badRequest("Certificate is not active: " + certNumber);
        }
        return cert;
    }

    public PageResponse<Certificate> listCertificates(Long developerId, Pageable pageable) {
        Page<Certificate> page;
        if (developerId != null) {
            page = certRepo.findByDeveloperId(developerId, pageable);
        } else {
            page = certRepo.findActiveCertificates(ZonedDateTime.now(), pageable);
        }
        return PageResponse.of(page.getContent(), page.getTotalElements(),
                page.getNumber(), page.getSize());
    }

    public List<Certificate> findExpiringSoon(int days) {
        ZonedDateTime now = ZonedDateTime.now();
        return certRepo.findExpiringSoon(now, now.plusDays(days));
    }

    // === Auth Chip Management ===

    @Transactional
    public AuthChip burnChip(Long certificateId, String chipType, String batchNumber) {
        Certificate cert = certRepo.findById(certificateId)
                .orElseThrow(() -> QooGearException.notFound("Certificate", certificateId));
        if (!cert.isActive()) {
            throw QooGearException.badRequest("Cannot burn chip for inactive certificate");
        }
        AuthChip chip = new AuthChip();
        chip.setCertificateId(certificateId);
        chip.setChipId(java.util.UUID.randomUUID().toString());
        chip.setChipType(chipType);
        chip.setBatchNumber(batchNumber);
        chip.setBurnedAt(ZonedDateTime.now());
        return chipRepo.save(chip);
    }

    public List<AuthChip> listChips(Long certificateId) {
        return chipRepo.findByCertificateId(certificateId);
    }

    // === Test Report Management ===

    public TestReport submitTestReport(Long appId, Long labId, String result, String summary) {
        TestReport report = new TestReport();
        report.setApplicationId(appId);
        report.setLaboratoryId(labId);
        report.setOverallResult(result);
        report.setSummary(summary);
        report.setSubmittedAt(ZonedDateTime.now());
        TestReport saved = testReportRepo.save(report);

        // Update application status
        CertApplication app = appRepo.findById(appId)
                .orElseThrow(() -> QooGearException.notFound("CertApplication", appId));
        app.setStatus(ApplicationStatus.TEST_COMPLETED.name().toLowerCase());
        appRepo.save(app);

        return saved;
    }

    public List<TestReport> getTestReports(Long appId) {
        return testReportRepo.findByApplicationId(appId);
    }
}
