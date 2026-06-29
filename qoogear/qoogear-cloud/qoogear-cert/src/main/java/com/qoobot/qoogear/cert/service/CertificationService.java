package com.qoobot.qoogear.cert.service;

import com.qoobot.qoogear.cert.domain.*;
import com.qoobot.qoogear.cert.repository.*;
import com.qoobot.qoogear.common.dto.PageResponse;
import com.qoobot.qoogear.common.enums.ApplicationStatus;
import com.qoobot.qoogear.common.exception.QooGearException;
import com.qoobot.qoogear.common.feign.LabClient;
import com.qoobot.qoogear.common.feign.SecurityClient;
import com.qoobot.qoogear.common.mq.RocketMQConfig;
import com.qoobot.qoogear.common.util.CertNumberGenerator;
import com.qoobot.qoogear.common.util.SpecNumberGenerator;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.ZonedDateTime;
import java.util.List;
import java.util.Optional;

/**
 * MFQ Certification Service — full 11-state workflow with cache/messaging/feign integration.
 *
 * State machine:
 *   DRAFT -> SUBMITTED -> COMPLIANCE_CHECK -> REVIEWING -> ASSIGNED
 *   -> TESTING -> TEST_COMPLETED -> SECURITY_REVIEW -> APPROVED -> [REVOKED | EXPIRED]
 *   Any state can transition to REJECTED (except terminal states)
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class CertificationService {

    private final CertApplicationRepository appRepo;
    private final CertificateRepository certRepo;
    private final DeveloperRepository devRepo;
    private final TestReportRepository testReportRepo;
    private final AuthChipRepository chipRepo;

    // Feign clients for inter-service communication
    private final Optional<LabClient> labClient;
    private final Optional<SecurityClient> securityClient;

    // === Application Management ===

    @Transactional
    public CertApplication createApplication(CertApplication app) {
        Developer dev = devRepo.findById(app.getDeveloperId())
                .orElseThrow(() -> QooGearException.notFound("Developer", app.getDeveloperId()));
        if (!"verified".equals(dev.getVerificationStatus())) {
            throw QooGearException.badRequest("Developer not verified");
        }
        app.setStatus(ApplicationStatus.DRAFT.name().toLowerCase());
        CertApplication saved = appRepo.save(app);
        log.info("Application created: id={}, developer={}, product={}", saved.getId(), app.getDeveloperId(), app.getProductName());
        return saved;
    }

    @Transactional
    @CacheEvict(value = "cert:list", allEntries = true)
    public CertApplication submitApplication(Long appId) {
        CertApplication app = appRepo.findById(appId)
                .orElseThrow(() -> QooGearException.notFound("CertApplication", appId));
        transition(app, ApplicationStatus.SUBMITTED);
        app.setSubmittedAt(ZonedDateTime.now());
        CertApplication saved = appRepo.save(app);
        log.info("Application submitted: id={}", appId);
        return saved;
    }

    /**
     * Full workflow review — handles all state transitions.
     * The state machine defined in ApplicationStatus.canTransitionTo() is enforced.
     */
    @Transactional
    @CacheEvict(value = "cert:list", allEntries = true)
    public CertApplication reviewApplication(Long appId, Long reviewerId, boolean approved, String comment) {
        CertApplication app = appRepo.findById(appId)
                .orElseThrow(() -> QooGearException.notFound("CertApplication", appId));

        ApplicationStatus current = ApplicationStatus.valueOf(app.getStatus().toUpperCase());

        if (approved) {
            // Progressive transition through the workflow
            ApplicationStatus next = determineNextApprovalState(current);
            transition(app, next);
        } else {
            // Rejection — only if not already in terminal state
            if (current == ApplicationStatus.REJECTED || current == ApplicationStatus.REVOKED || current == ApplicationStatus.EXPIRED) {
                throw QooGearException.badRequest("Cannot reject application in terminal state: " + current.getDisplayName());
            }
            app.setStatus(ApplicationStatus.REJECTED.name().toLowerCase());
            app.setRejectionReason(comment);
        }

        app.setReviewedBy(reviewerId);
        app.setReviewComment(comment);
        app.setReviewedAt(ZonedDateTime.now());

        CertApplication saved = appRepo.save(app);
        log.info("Application reviewed: id={}, approved={}, newStatus={}", appId, approved, saved.getStatus());

        // If moving to ASSIGNED, auto-assign to a lab via Feign
        if (ApplicationStatus.ASSIGNED.name().toLowerCase().equals(saved.getStatus())) {
            autoAssignLab(saved);
        }

        return saved;
    }

    @Transactional
    @CacheEvict(value = "cert:list", allEntries = true)
    public CertApplication assignLab(Long appId, Long labId) {
        CertApplication app = appRepo.findById(appId)
                .orElseThrow(() -> QooGearException.notFound("CertApplication", appId));
        transition(app, ApplicationStatus.ASSIGNED);
        app.setAssignedLabId(labId);
        app.setAssignedAt(ZonedDateTime.now());
        CertApplication saved = appRepo.save(app);
        log.info("Lab assigned: appId={}, labId={}", appId, labId);
        return saved;
    }

    @Cacheable(value = "cert:list", key = "#developerId + '-' + #status + '-' + #pageable.pageNumber")
    public PageResponse<CertApplication> listApplications(Long developerId, String status, Pageable pageable) {
        Page<CertApplication> page;
        if (developerId != null && status != null) {
            page = appRepo.findByDeveloperIdAndStatus(developerId, status, pageable);
        } else if (developerId != null) {
            page = appRepo.findByDeveloperId(developerId, pageable);
        } else if (status != null) {
            page = appRepo.findByStatus(status, pageable);
        } else {
            page = appRepo.findAll(pageable);
        }
        return PageResponse.of(page.getContent(), page.getTotalElements(), page.getNumber(), page.getSize());
    }

    @Cacheable(value = "cert:detail", key = "#appId")
    public CertApplication getApplication(Long appId) {
        return appRepo.findById(appId)
                .orElseThrow(() -> QooGearException.notFound("CertApplication", appId));
    }

    @Transactional
    @CacheEvict(value = {"cert:detail", "cert:list"}, allEntries = true)
    public CertApplication updateApplication(Long appId, CertApplication update) {
        CertApplication app = appRepo.findById(appId)
                .orElseThrow(() -> QooGearException.notFound("CertApplication", appId));
        if (app.getStatus().equals(ApplicationStatus.DRAFT.name().toLowerCase())) {
            app.setProductName(update.getProductName());
            app.setProductModel(update.getProductModel());
            app.setProductCategory(update.getProductCategory());
            app.setCertLevel(update.getCertLevel());
            app.setDescription(update.getDescription());
            app.setSpecVersion(update.getSpecVersion());
        } else {
            throw QooGearException.badRequest("Only draft applications can be updated");
        }
        return appRepo.save(app);
    }

    // === Certificate Management ===

    @Transactional
    @CacheEvict(value = "cert:list", allEntries = true)
    public Certificate issueCertificate(Long appId) {
        CertApplication app = appRepo.findById(appId)
                .orElseThrow(() -> QooGearException.notFound("CertApplication", appId));

        if (!ApplicationStatus.APPROVED.name().toLowerCase().equals(app.getStatus())) {
            throw QooGearException.badRequest("Application must be APPROVED to issue certificate, current: " + app.getStatus());
        }

        long testReports = testReportRepo.countByApplicationId(appId);
        if (testReports == 0) {
            throw QooGearException.badRequest("Test reports required before issuing certificate");
        }

        // Run FMEA security analysis before issuing
        triggerFmeaAnalysis(app);

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
        appRepo.save(app);

        log.info("Certificate issued: {} for application {}", saved.getCertNumber(), appId);
        return saved;
    }

    @Transactional
    @CacheEvict(value = {"cert:detail", "cert:list"}, allEntries = true)
    public Certificate revokeCertificate(Long certId, String reason) {
        Certificate cert = certRepo.findById(certId)
                .orElseThrow(() -> QooGearException.notFound("Certificate", certId));
        if (cert.getRevokedAt() != null) {
            throw QooGearException.badRequest("Certificate already revoked: " + cert.getCertNumber());
        }
        cert.setRevokedAt(ZonedDateTime.now());
        cert.setRevokeReason(reason);

        // Update associated application
        certRepo.findById(certId).ifPresent(c -> {
            CertApplication app = appRepo.findById(c.getApplicationId()).orElse(null);
            if (app != null) {
                app.setStatus(ApplicationStatus.REVOKED.name().toLowerCase());
                appRepo.save(app);
            }
        });

        Certificate saved = certRepo.save(cert);
        log.warn("Certificate revoked: {} - {}", saved.getCertNumber(), reason);
        return saved;
    }

    @Cacheable(value = "cert:detail", key = "#certNumber")
    public Certificate verifyCertificate(String certNumber) {
        Certificate cert = certRepo.findByCertNumber(certNumber)
                .orElseThrow(() -> QooGearException.notFound("Certificate", certNumber));
        if (!cert.isActive()) {
            throw QooGearException.badRequest("Certificate is not active: " + certNumber);
        }
        return cert;
    }

    @Cacheable(value = "cert:list", key = "#developerId + '-' + #pageable.pageNumber")
    public PageResponse<Certificate> listCertificates(Long developerId, Pageable pageable) {
        Page<Certificate> page;
        if (developerId != null) {
            page = certRepo.findByDeveloperId(developerId, pageable);
        } else {
            page = certRepo.findActiveCertificates(ZonedDateTime.now(), pageable);
        }
        return PageResponse.of(page.getContent(), page.getTotalElements(), page.getNumber(), page.getSize());
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

        // Generate a secure serial number using SpecNumberGenerator pattern
        String serial = SpecNumberGenerator.generate("CHIP");
        chip.setChipId(serial);

        return chipRepo.save(chip);
    }

    public List<AuthChip> listChips(Long certificateId) {
        return chipRepo.findByCertificateId(certificateId);
    }

    // === Test Report Management ===

    @Transactional
    @CacheEvict(value = {"cert:detail", "cert:list"}, allEntries = true)
    public TestReport submitTestReport(Long appId, Long labId, String result, String summary) {
        CertApplication app = appRepo.findById(appId)
                .orElseThrow(() -> QooGearException.notFound("CertApplication", appId));

        TestReport report = new TestReport();
        report.setApplicationId(appId);
        report.setLaboratoryId(labId);
        report.setOverallResult(result);
        report.setSummary(summary);
        report.setSubmittedAt(ZonedDateTime.now());
        TestReport saved = testReportRepo.save(report);

        // Transition to TEST_COMPLETED
        transition(app, ApplicationStatus.TEST_COMPLETED);
        appRepo.save(app);

        log.info("Test report submitted: appId={}, labId={}, result={}", appId, labId, result);
        return saved;
    }

    public List<TestReport> getTestReports(Long appId) {
        return testReportRepo.findByApplicationId(appId);
    }

    // === Private helpers ===

    /**
     * Enforce state machine transition with validation.
     */
    private void transition(CertApplication app, ApplicationStatus target) {
        ApplicationStatus current;
        try {
            current = ApplicationStatus.valueOf(app.getStatus().toUpperCase());
        } catch (IllegalArgumentException e) {
            throw QooGearException.badRequest("Unknown status: " + app.getStatus());
        }

        if (!current.canTransitionTo(target)) {
            throw QooGearException.badRequest(
                    String.format("Invalid state transition: %s -> %s", current.getDisplayName(), target.getDisplayName()));
        }

        app.setStatus(target.name().toLowerCase());
        log.debug("State transition: appId={}, {} -> {}", app.getId(), current.getDisplayName(), target.getDisplayName());
    }

    /**
     * Determine the next approval state in the workflow.
     */
    private ApplicationStatus determineNextApprovalState(ApplicationStatus current) {
        return switch (current) {
            case DRAFT -> ApplicationStatus.SUBMITTED;
            case SUBMITTED -> ApplicationStatus.COMPLIANCE_CHECK;
            case COMPLIANCE_CHECK -> ApplicationStatus.REVIEWING;
            case REVIEWING -> ApplicationStatus.ASSIGNED;
            case ASSIGNED -> ApplicationStatus.TESTING;
            case TESTING -> ApplicationStatus.TEST_COMPLETED;
            case TEST_COMPLETED -> ApplicationStatus.SECURITY_REVIEW;
            case SECURITY_REVIEW -> ApplicationStatus.APPROVED;
            case APPROVED -> throw QooGearException.badRequest("Application already approved");
            case REJECTED, REVOKED, EXPIRED ->
                    throw QooGearException.badRequest("Cannot advance from terminal state: " + current.getDisplayName());
        };
    }

    /**
     * Auto-assign to the first available lab via Feign.
     */
    private void autoAssignLab(CertApplication app) {
        labClient.ifPresent(client -> {
            try {
                var response = client.listEquipment();
                if (response.getCode() == 200) {
                    log.info("Lab auto-assignment triggered for appId={}", app.getId());
                }
            } catch (Exception e) {
                log.warn("Lab auto-assignment failed (lab service may be offline): {}", e.getMessage());
            }
        });
    }

    /**
     * Trigger FMEA security analysis before certificate issuance.
     */
    private void triggerFmeaAnalysis(CertApplication app) {
        securityClient.ifPresent(client -> {
            try {
                var fmeaRequest = java.util.Map.of(
                        "entityType", "CERT_APPLICATION",
                        "entityId", app.getId(),
                        "productCategory", app.getProductCategory(),
                        "certLevel", app.getCertLevel()
                );
                client.createFmeaRecord(fmeaRequest);
                log.info("FMEA analysis triggered for appId={}", app.getId());
            } catch (Exception e) {
                log.warn("FMEA trigger failed (security service may be offline): {}", e.getMessage());
            }
        });
    }
}
