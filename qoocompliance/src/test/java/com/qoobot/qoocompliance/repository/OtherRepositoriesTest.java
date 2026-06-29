package com.qoobot.qoocompliance.repository;

import com.qoobot.qoocompliance.domain.CertificationProgress;
import com.qoobot.qoocompliance.domain.ComplianceReview;
import com.qoobot.qoocompliance.domain.RegulationChange;
import com.qoobot.qoocompliance.domain.AuditRecord;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;
import org.springframework.test.context.ActiveProfiles;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
@ActiveProfiles("test")
@DisplayName("CertificationProgressRepository")
class CertificationProgressRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private CertificationProgressRepository repository;

    private CertificationProgress fcc;
    private CertificationProgress ce;

    @BeforeEach
    void setUp() {
        fcc = new CertificationProgress();
        fcc.setProductId("PROD-001");
        fcc.setMarket("US");
        fcc.setCertType("FCC");
        fcc.setCertNumber("FCC-2024-001");
        fcc.setStatus("APPROVED");
        fcc.setAppliedAt(LocalDate.of(2024, 1, 15));
        fcc.setApprovedAt(LocalDate.of(2024, 3, 20));
        fcc.setExpiresAt(LocalDate.of(2029, 3, 20));
        fcc.setLabName("SGS Lab");
        entityManager.persist(fcc);

        ce = new CertificationProgress();
        ce.setProductId("PROD-001");
        ce.setMarket("EU");
        ce.setCertType("CE_RED");
        ce.setCertNumber("CE-2024-001");
        ce.setStatus("IN_PROGRESS");
        ce.setAppliedAt(LocalDate.of(2024, 2, 1));
        ce.setLabName("TUV Rheinland");
        entityManager.persist(ce);

        entityManager.flush();
    }

    @Nested
    @DisplayName("findByProductId")
    class FindByProductId {
        @Test
        void shouldFindByProductId() {
            List<CertificationProgress> result = repository.findByProductId("PROD-001");
            assertThat(result).hasSize(2);
        }
    }

    @Nested
    @DisplayName("findByMarket")
    class FindByMarket {
        @Test
        void shouldFindByMarket() {
            List<CertificationProgress> result = repository.findByMarket("US");
            assertThat(result).hasSize(1);
            assertThat(result.get(0).getCertType()).isEqualTo("FCC");
        }
    }

    @Nested
    @DisplayName("findByStatus")
    class FindByStatus {
        @Test
        void shouldFindApproved() {
            List<CertificationProgress> result = repository.findByStatus("APPROVED");
            assertThat(result).hasSize(1);
        }
    }

    @Nested
    @DisplayName("findByProductIdAndMarket")
    class FindByProductIdAndMarket {
        @Test
        void shouldFindByProductAndMarket() {
            List<CertificationProgress> result = repository.findByProductIdAndMarket("PROD-001", "EU");
            assertThat(result).hasSize(1);
        }
    }

    @Nested
    @DisplayName("findByCertNumber")
    class FindByCertNumber {
        @Test
        void shouldFindByCertNumber() {
            Optional<CertificationProgress> result = repository.findByCertNumber("FCC-2024-001");
            assertThat(result).isPresent();
        }
    }

    @Nested
    @DisplayName("findByProductIdAndStatus")
    class FindByProductIdAndStatus {
        @Test
        void shouldFindByProductAndStatus() {
            List<CertificationProgress> result = repository.findByProductIdAndStatus("PROD-001", "IN_PROGRESS");
            assertThat(result).hasSize(1);
        }
    }
}

@DataJpaTest
@ActiveProfiles("test")
@DisplayName("ComplianceReviewRepository")
class ComplianceReviewRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private ComplianceReviewRepository repository;

    @BeforeEach
    void setUp() {
        ComplianceReview review = new ComplianceReview();
        review.setProductId("PROD-001");
        review.setReviewType("SAFETY_AUDIT");
        review.setStatus("PASSED");
        review.setFindings("All safety requirements met");
        review.setReviewerId("REV-001");
        review.setReviewerName("Zhang Wei");
        entityManager.persist(review);

        ComplianceReview review2 = new ComplianceReview();
        review2.setProductId("PROD-001");
        review2.setReviewType("PRIVACY_AUDIT");
        review2.setStatus("IN_PROGRESS");
        review2.setReviewerId("REV-002");
        review2.setReviewerName("Li Ming");
        entityManager.persist(review2);

        entityManager.flush();
    }

    @Test
    @DisplayName("should find reviews by productId")
    void shouldFindByProductId() {
        List<ComplianceReview> result = repository.findByProductId("PROD-001");
        assertThat(result).hasSize(2);
    }

    @Test
    @DisplayName("should find by reviewType")
    void shouldFindByReviewType() {
        List<ComplianceReview> result = repository.findByReviewType("SAFETY_AUDIT");
        assertThat(result).hasSize(1);
    }

    @Test
    @DisplayName("should find by status")
    void shouldFindByStatus() {
        List<ComplianceReview> result = repository.findByStatus("PASSED");
        assertThat(result).hasSize(1);
    }

    @Test
    @DisplayName("should find by reviewerId")
    void shouldFindByReviewerId() {
        List<ComplianceReview> result = repository.findByReviewerId("REV-001");
        assertThat(result).hasSize(1);
    }

    @Test
    @DisplayName("should find by productId and status")
    void shouldFindByProductAndStatus() {
        List<ComplianceReview> result = repository.findByProductIdAndStatus("PROD-001", "IN_PROGRESS");
        assertThat(result).hasSize(1);
    }

    @Test
    @DisplayName("should find by productId and reviewType")
    void shouldFindByProductAndReviewType() {
        List<ComplianceReview> result = repository.findByProductIdAndReviewType("PROD-001", "PRIVACY_AUDIT");
        assertThat(result).hasSize(1);
    }
}

@DataJpaTest
@ActiveProfiles("test")
@DisplayName("RegulationChangeRepository")
class RegulationChangeRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private RegulationChangeRepository repository;

    @BeforeEach
    void setUp() {
        RegulationChange change = new RegulationChange();
        change.setRegulationId("EU-REG-001");
        change.setMarket("EU");
        change.setChangeType("AMENDMENT");
        change.setTitle("GDPR Amendment 2024");
        change.setDescription("New data transfer requirements");
        change.setImpactLevel("HIGH");
        change.setEffectiveDate(LocalDate.of(2024, 6, 1));
        change.setNotified(false);
        entityManager.persist(change);

        RegulationChange change2 = new RegulationChange();
        change2.setRegulationId("CN-REG-001");
        change2.setMarket("CN");
        change2.setChangeType("UPDATE");
        change2.setTitle("PIPL Implementation Rules");
        change2.setDescription("Detailed implementation guidelines");
        change2.setImpactLevel("MEDIUM");
        change2.setNotified(true);
        entityManager.persist(change2);

        entityManager.flush();
    }

    @Test
    @DisplayName("should find by regulationId")
    void shouldFindByRegulationId() {
        List<RegulationChange> result = repository.findByRegulationId("EU-REG-001");
        assertThat(result).hasSize(1);
    }

    @Test
    @DisplayName("should find by changeType")
    void shouldFindByChangeType() {
        List<RegulationChange> result = repository.findByChangeType("AMENDMENT");
        assertThat(result).hasSize(1);
    }

    @Test
    @DisplayName("should find by impactLevel")
    void shouldFindByImpactLevel() {
        List<RegulationChange> result = repository.findByImpactLevel("HIGH");
        assertThat(result).hasSize(1);
    }

    @Test
    @DisplayName("should find unnotified changes")
    void shouldFindUnnotified() {
        List<RegulationChange> result = repository.findByNotified(false);
        assertThat(result).hasSize(1);
    }
}

@DataJpaTest
@ActiveProfiles("test")
@DisplayName("AuditRecordRepository")
class AuditRecordRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private AuditRecordRepository repository;

    @BeforeEach
    void setUp() {
        AuditRecord record = new AuditRecord();
        record.setAction("CHECKLIST_CREATED");
        record.setProductId("PROD-001");
        record.setMarket("EU");
        record.setUserId("USER-001");
        record.setDetails("Created EU compliance checklist");
        entityManager.persist(record);

        AuditRecord record2 = new AuditRecord();
        record2.setAction("ITEM_UPDATED");
        record2.setProductId("PROD-001");
        record2.setMarket("EU");
        record2.setUserId("USER-002");
        record2.setDetails("Updated CE RED item to COMPLIANT");
        entityManager.persist(record2);

        entityManager.flush();
    }

    @Test
    @DisplayName("should find by productId")
    void shouldFindByProductId() {
        List<AuditRecord> result = repository.findByProductId("PROD-001");
        assertThat(result).hasSize(2);
    }

    @Test
    @DisplayName("should find by action")
    void shouldFindByAction() {
        List<AuditRecord> result = repository.findByAction("CHECKLIST_CREATED");
        assertThat(result).hasSize(1);
    }

    @Test
    @DisplayName("should find by userId")
    void shouldFindByUserId() {
        List<AuditRecord> result = repository.findByUserId("USER-001");
        assertThat(result).hasSize(1);
    }

    @Test
    @DisplayName("should find by productId and action")
    void shouldFindByProductAndAction() {
        List<AuditRecord> result = repository.findByProductIdAndAction("PROD-001", "ITEM_UPDATED");
        assertThat(result).hasSize(1);
    }

    @Test
    @DisplayName("should find by market")
    void shouldFindByMarket() {
        List<AuditRecord> result = repository.findByMarket("EU");
        assertThat(result).hasSize(2);
    }
}
