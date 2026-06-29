package com.qoobot.qoogear.cert.service;

import com.qoobot.qoogear.cert.domain.*;
import com.qoobot.qoogear.cert.repository.*;
import com.qoobot.qoogear.common.enums.ApplicationStatus;
import com.qoobot.qoogear.common.exception.QooGearException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.ZonedDateTime;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Unit tests for CertificationService — state machine transitions and business logic.
 */
@ExtendWith(MockitoExtension.class)
class CertificationServiceTest {

    @Mock private CertApplicationRepository appRepo;
    @Mock private CertificateRepository certRepo;
    @Mock private DeveloperRepository devRepo;
    @Mock private TestReportRepository testReportRepo;
    @Mock private AuthChipRepository chipRepo;

    @InjectMocks
    private CertificationService service;

    private Developer developer;
    private CertApplication application;

    @BeforeEach
    void setUp() {
        developer = new Developer();
        developer.setId(1L);
        developer.setVerificationStatus("verified");

        application = new CertApplication();
        application.setId(1L);
        application.setDeveloperId(1L);
        application.setProductName("TestGripper");
        application.setProductModel("TG-001");
        application.setProductCategory("gripper");
        application.setCertLevel("premium");
        application.setStatus(ApplicationStatus.DRAFT.name().toLowerCase());
    }

    @Test
    void shouldCreateApplicationWhenDeveloperIsVerified() {
        when(devRepo.findById(1L)).thenReturn(Optional.of(developer));
        when(appRepo.save(any(CertApplication.class))).thenReturn(application);

        CertApplication result = service.createApplication(application);

        assertNotNull(result);
        assertEquals(ApplicationStatus.DRAFT.name().toLowerCase(), result.getStatus());
        verify(appRepo).save(application);
    }

    @Test
    void shouldRejectApplicationWhenDeveloperNotVerified() {
        developer.setVerificationStatus("pending");
        when(devRepo.findById(1L)).thenReturn(Optional.of(developer));

        assertThrows(QooGearException.class, () -> service.createApplication(application));
    }

    @Test
    void shouldSubmitDraftApplication() {
        when(appRepo.findById(1L)).thenReturn(Optional.of(application));
        when(appRepo.save(any(CertApplication.class))).thenReturn(application);

        CertApplication result = service.submitApplication(1L);

        assertEquals(ApplicationStatus.SUBMITTED.name().toLowerCase(), result.getStatus());
        assertNotNull(result.getSubmittedAt());
    }

    @Test
    void shouldRejectSubmitWhenNotDraft() {
        application.setStatus(ApplicationStatus.SUBMITTED.name().toLowerCase());
        when(appRepo.findById(1L)).thenReturn(Optional.of(application));

        assertThrows(QooGearException.class, () -> service.submitApplication(1L));
    }

    @Test
    void shouldProgressThroughReviewWorkflow() {
        application.setStatus(ApplicationStatus.SUBMITTED.name().toLowerCase());
        when(appRepo.findById(1L)).thenReturn(Optional.of(application));
        when(appRepo.save(any(CertApplication.class))).thenReturn(application);

        CertApplication result = service.reviewApplication(1L, 100L, true, "Looks good");

        assertEquals(ApplicationStatus.COMPLIANCE_CHECK.name().toLowerCase(), result.getStatus());
        assertEquals(100L, result.getReviewedBy());
    }

    @Test
    void shouldRejectApplicationOnReview() {
        application.setStatus(ApplicationStatus.SUBMITTED.name().toLowerCase());
        when(appRepo.findById(1L)).thenReturn(Optional.of(application));
        when(appRepo.save(any(CertApplication.class))).thenReturn(application);

        CertApplication result = service.reviewApplication(1L, 100L, false, "Incomplete docs");

        assertEquals(ApplicationStatus.REJECTED.name().toLowerCase(), result.getStatus());
        assertEquals("Incomplete docs", result.getRejectionReason());
    }

    @Test
    void shouldNotIssueCertificateWithoutTestReports() {
        application.setStatus(ApplicationStatus.APPROVED.name().toLowerCase());
        when(appRepo.findById(1L)).thenReturn(Optional.of(application));
        when(testReportRepo.countByApplicationId(1L)).thenReturn(0L);

        assertThrows(QooGearException.class, () -> service.issueCertificate(1L));
    }

    @Test
    void shouldIssueCertificateWhenApproved() {
        application.setStatus(ApplicationStatus.APPROVED.name().toLowerCase());
        when(appRepo.findById(1L)).thenReturn(Optional.of(application));
        when(testReportRepo.countByApplicationId(1L)).thenReturn(2L);
        when(certRepo.save(any(Certificate.class))).thenAnswer(inv -> {
            Certificate c = inv.getArgument(0);
            c.setId(1L);
            return c;
        });

        Certificate cert = service.issueCertificate(1L);

        assertNotNull(cert);
        assertNotNull(cert.getCertNumber());
        assertTrue(cert.getCertNumber().startsWith("MFQ-"));
        assertEquals(1L, cert.getDeveloperId());
        assertNotNull(cert.getExpiresAt());
    }

    @Test
    void shouldValidateActiveCertificate() {
        Certificate cert = new Certificate();
        cert.setId(1L);
        cert.setCertNumber("MFQ-2026-PREMIUM-0001");
        cert.setIssuedAt(ZonedDateTime.now().minusDays(30));
        cert.setExpiresAt(ZonedDateTime.now().plusDays(700));

        when(certRepo.findByCertNumber("MFQ-2026-PREMIUM-0001")).thenReturn(Optional.of(cert));

        Certificate result = service.verifyCertificate("MFQ-2026-PREMIUM-0001");

        assertNotNull(result);
        assertTrue(result.isActive());
    }

    @Test
    void shouldRejectExpiredCertificate() {
        Certificate cert = new Certificate();
        cert.setId(1L);
        cert.setCertNumber("MFQ-2024-PREMIUM-0001");
        cert.setIssuedAt(ZonedDateTime.now().minusYears(3));
        cert.setExpiresAt(ZonedDateTime.now().minusDays(1));

        when(certRepo.findByCertNumber("MFQ-2024-PREMIUM-0001")).thenReturn(Optional.of(cert));

        assertThrows(QooGearException.class, () -> service.verifyCertificate("MFQ-2024-PREMIUM-0001"));
    }

    @Test
    void shouldRevokeCertificate() {
        Certificate cert = new Certificate();
        cert.setId(1L);
        cert.setCertNumber("MFQ-2026-PREMIUM-0001");

        when(certRepo.findById(1L)).thenReturn(Optional.of(cert));
        when(certRepo.save(any(Certificate.class))).thenReturn(cert);

        Certificate result = service.revokeCertificate(1L, "Safety violation");

        assertNotNull(result.getRevokedAt());
        assertEquals("Safety violation", result.getRevokeReason());
    }

    @Test
    void shouldSubmitTestReport() {
        application.setStatus(ApplicationStatus.TESTING.name().toLowerCase());
        when(appRepo.findById(1L)).thenReturn(Optional.of(application));
        when(testReportRepo.save(any(TestReport.class))).thenAnswer(inv -> {
            TestReport r = inv.getArgument(0);
            r.setId(1L);
            return r;
        });

        TestReport report = service.submitTestReport(1L, 10L, "pass", "All tests passed");

        assertNotNull(report);
        assertEquals("pass", report.getOverallResult());
        assertEquals(ApplicationStatus.TEST_COMPLETED.name().toLowerCase(), application.getStatus());
    }
}
