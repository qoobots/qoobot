package com.qoobot.qoocompliance.repository;

import com.qoobot.qoocompliance.domain.ComplianceItem;
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
@DisplayName("ComplianceItemRepository")
class ComplianceItemRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private ComplianceItemRepository repository;

    private ComplianceItem item1;
    private ComplianceItem item2;
    private ComplianceItem item3;

    @BeforeEach
    void setUp() {
        item1 = new ComplianceItem();
        item1.setItemId("CL-001-ITEM-001");
        item1.setChecklistId("CL-001");
        item1.setProjectId("PROJ-001");
        item1.setCategory("ROBOT_SAFETY");
        item1.setTitle("CE 机械指令");
        item1.setPriority("P0");
        item1.setStatus("NOT_STARTED");
        item1.setMarket("EU");
        entityManager.persist(item1);

        item2 = new ComplianceItem();
        item2.setItemId("CL-001-ITEM-002");
        item2.setChecklistId("CL-001");
        item2.setProjectId("PROJ-001");
        item2.setCategory("WIRELESS_EMC");
        item2.setTitle("CE RED 指令");
        item2.setPriority("P0");
        item2.setStatus("COMPLIANT");
        item2.setMarket("EU");
        entityManager.persist(item2);

        item3 = new ComplianceItem();
        item3.setItemId("CL-002-ITEM-001");
        item3.setChecklistId("CL-002");
        item3.setProjectId("PROJ-002");
        item3.setCategory("PRIVACY_DATA");
        item3.setTitle("PIPL 合规");
        item3.setPriority("P0");
        item3.setStatus("IN_PROGRESS");
        item3.setMarket("CN");
        entityManager.persist(item3);

        entityManager.flush();
    }

    @Nested
    @DisplayName("findByItemId")
    class FindByItemId {

        @Test
        @DisplayName("should find existing item")
        void shouldFindExistingItem() {
            Optional<ComplianceItem> result = repository.findByItemId("CL-001-ITEM-001");
            assertThat(result).isPresent();
            assertThat(result.get().getTitle()).isEqualTo("CE 机械指令");
        }
    }

    @Nested
    @DisplayName("findByChecklistId")
    class FindByChecklistId {

        @Test
        @DisplayName("should find items by checklistId")
        void shouldFindByChecklistId() {
            List<ComplianceItem> result = repository.findByChecklistId("CL-001");
            assertThat(result).hasSize(2);
        }
    }

    @Nested
    @DisplayName("findByProjectId")
    class FindByProjectId {

        @Test
        @DisplayName("should find items by projectId")
        void shouldFindByProjectId() {
            List<ComplianceItem> result = repository.findByProjectId("PROJ-001");
            assertThat(result).hasSize(2);
        }
    }

    @Nested
    @DisplayName("findByCategory")
    class FindByCategory {

        @Test
        @DisplayName("should find items by category")
        void shouldFindByCategory() {
            List<ComplianceItem> result = repository.findByCategory("ROBOT_SAFETY");
            assertThat(result).hasSize(1);
        }
    }

    @Nested
    @DisplayName("findByStatus")
    class FindByStatus {

        @Test
        @DisplayName("should find items by status")
        void shouldFindByStatus() {
            List<ComplianceItem> result = repository.findByStatus("COMPLIANT");
            assertThat(result).hasSize(1);
            assertThat(result.get(0).getTitle()).isEqualTo("CE RED 指令");
        }
    }

    @Nested
    @DisplayName("findByPriority")
    class FindByPriority {

        @Test
        @DisplayName("should find P0 items")
        void shouldFindP0Items() {
            List<ComplianceItem> result = repository.findByPriority("P0");
            assertThat(result).hasSize(3);
        }
    }

    @Nested
    @DisplayName("findByChecklistIdAndCategory")
    class FindByChecklistIdAndCategory {

        @Test
        @DisplayName("should filter by checklistId and category")
        void shouldFilterByChecklistAndCategory() {
            List<ComplianceItem> result = repository.findByChecklistIdAndCategory("CL-001", "WIRELESS_EMC");
            assertThat(result).hasSize(1);
        }
    }

    @Nested
    @DisplayName("findByChecklistIdAndStatus")
    class FindByChecklistIdAndStatus {

        @Test
        @DisplayName("should filter by checklistId and status")
        void shouldFilterByChecklistAndStatus() {
            List<ComplianceItem> result = repository.findByChecklistIdAndStatus("CL-001", "NOT_STARTED");
            assertThat(result).hasSize(1);
        }
    }

    @Nested
    @DisplayName("findByChecklistIdAndCategoryAndStatus")
    class FindByChecklistIdAndCategoryAndStatus {

        @Test
        @DisplayName("should filter by checklistId, category and status")
        void shouldFilterByAllThree() {
            List<ComplianceItem> result = repository.findByChecklistIdAndCategoryAndStatus(
                    "CL-001", "ROBOT_SAFETY", "NOT_STARTED");
            assertThat(result).hasSize(1);
        }

        @Test
        @DisplayName("should return empty for no match")
        void shouldReturnEmptyForNoMatch() {
            List<ComplianceItem> result = repository.findByChecklistIdAndCategoryAndStatus(
                    "CL-001", "ROBOT_SAFETY", "COMPLIANT");
            assertThat(result).isEmpty();
        }
    }
}
