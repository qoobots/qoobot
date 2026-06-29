package com.qoobot.qoocompliance.repository;

import com.qoobot.qoocompliance.domain.ComplianceChecklist;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;
import org.springframework.test.context.ActiveProfiles;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
@ActiveProfiles("test")
@DisplayName("ComplianceChecklistRepository")
class ComplianceChecklistRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private ComplianceChecklistRepository repository;

    private ComplianceChecklist checklist1;
    private ComplianceChecklist checklist2;

    @BeforeEach
    void setUp() {
        checklist1 = new ComplianceChecklist();
        checklist1.setChecklistId("CL-001");
        checklist1.setProjectId("PROJ-001");
        checklist1.setProjectName("QooBot EU Launch");
        checklist1.setMarket("EU");
        checklist1.setTargetMarkets("EU,US");
        checklist1.setStatus("ACTIVE");
        entityManager.persist(checklist1);

        checklist2 = new ComplianceChecklist();
        checklist2.setChecklistId("CL-002");
        checklist2.setProjectId("PROJ-002");
        checklist2.setProjectName("QooBot CN Launch");
        checklist2.setMarket("CN");
        checklist2.setTargetMarkets("CN");
        checklist2.setStatus("DRAFT");
        entityManager.persist(checklist2);

        entityManager.flush();
    }

    @Nested
    @DisplayName("findByChecklistId")
    class FindByChecklistId {

        @Test
        @DisplayName("should find by checklistId")
        void shouldFindByChecklistId() {
            Optional<ComplianceChecklist> result = repository.findByChecklistId("CL-001");
            assertThat(result).isPresent();
            assertThat(result.get().getProjectName()).isEqualTo("QooBot EU Launch");
        }
    }

    @Nested
    @DisplayName("findByProjectId")
    class FindByProjectId {

        @Test
        @DisplayName("should find by projectId")
        void shouldFindByProjectId() {
            List<ComplianceChecklist> result = repository.findByProjectId("PROJ-001");
            assertThat(result).hasSize(1);
        }
    }

    @Nested
    @DisplayName("findByMarket")
    class FindByMarket {

        @Test
        @DisplayName("should find by market")
        void shouldFindByMarket() {
            List<ComplianceChecklist> result = repository.findByMarket("EU");
            assertThat(result).hasSize(1);
        }
    }

    @Nested
    @DisplayName("findByStatus")
    class FindByStatus {

        @Test
        @DisplayName("should find active checklists")
        void shouldFindActiveChecklists() {
            List<ComplianceChecklist> result = repository.findByStatus("ACTIVE");
            assertThat(result).hasSize(1);
        }
    }

    @Nested
    @DisplayName("findByProjectIdAndMarket")
    class FindByProjectIdAndMarket {

        @Test
        @DisplayName("should find by projectId and market")
        void shouldFindByProjectIdAndMarket() {
            List<ComplianceChecklist> result = repository.findByProjectIdAndMarket("PROJ-001", "EU");
            assertThat(result).hasSize(1);
        }
    }
}
