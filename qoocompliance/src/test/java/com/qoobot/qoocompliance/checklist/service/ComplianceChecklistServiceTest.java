package com.qoobot.qoocompliance.checklist.service;

import com.qoobot.qoocompliance.checklist.service.ComplianceChecklistService.*;
import com.qoobot.qoocompliance.domain.ComplianceChecklist;
import com.qoobot.qoocompliance.domain.ComplianceItem;
import com.qoobot.qoocompliance.repository.ComplianceChecklistRepository;
import com.qoobot.qoocompliance.repository.ComplianceItemRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("ComplianceChecklistService")
class ComplianceChecklistServiceTest {

    @Mock
    private ComplianceChecklistRepository checklistRepo;

    @Mock
    private ComplianceItemRepository itemRepo;

    @InjectMocks
    private ComplianceChecklistService service;

    @Captor
    private ArgumentCaptor<ComplianceChecklist> checklistCaptor;

    @Captor
    private ArgumentCaptor<List<ComplianceItem>> itemsCaptor;

    private static final String PROJECT_ID = "test-project-id";

    @Nested
    @DisplayName("generateChecklist")
    class GenerateChecklist {

        @Test
        @DisplayName("should create checklist and items for target markets")
        void shouldCreateChecklistAndItems() {
            when(checklistRepo.save(any(ComplianceChecklist.class))).thenAnswer(inv -> inv.getArgument(0));
            when(itemRepo.saveAll(anyList())).thenAnswer(inv -> inv.getArgument(0));

            ComplianceProject result = service.generateChecklist("Test Project", List.of("CN", "EU"));

            assertThat(result).isNotNull();
            assertThat(result.name()).isEqualTo("Test Project");
            assertThat(result.targetMarkets()).containsExactly("CN", "EU");
            assertThat(result.status()).isEqualTo("DRAFT");

            verify(checklistRepo).save(any(ComplianceChecklist.class));
            verify(itemRepo).saveAll(anyList());
        }

        @Test
        @DisplayName("should handle empty market list")
        void shouldHandleEmptyMarkets() {
            when(checklistRepo.save(any(ComplianceChecklist.class))).thenAnswer(inv -> inv.getArgument(0));
            when(itemRepo.saveAll(anyList())).thenReturn(List.of());

            ComplianceProject result = service.generateChecklist("Empty Project", List.of());

            assertThat(result).isNotNull();
            assertThat(result.targetMarkets()).isEmpty();
        }
    }

    @Nested
    @DisplayName("getItems")
    class GetItems {

        @Test
        @DisplayName("should return all items without filters")
        void shouldReturnAllItems() {
            ComplianceItem entity = createItemEntity("ITEM-001", "CN", "ROBOT_SAFETY", "P0", "NOT_STARTED");
            when(itemRepo.findByChecklistId(PROJECT_ID)).thenReturn(List.of(entity));

            List<ComplianceItem> result = service.getItems(PROJECT_ID, null, null);

            assertThat(result).hasSize(1);
            assertThat(result.get(0).getItemId()).isEqualTo("ITEM-001");
        }

        @Test
        @DisplayName("should filter by category")
        void shouldFilterByCategory() {
            ComplianceItem entity1 = createItemEntity("ITEM-001", "CN", "ROBOT_SAFETY", "P0", "NOT_STARTED");
            ComplianceItem entity2 = createItemEntity("ITEM-002", "CN", "WIRELESS_EMC", "P0", "NOT_STARTED");
            when(itemRepo.findByChecklistId(PROJECT_ID)).thenReturn(List.of(entity1, entity2));

            List<ComplianceItem> result = service.getItems(PROJECT_ID, "ROBOT_SAFETY", null);

            assertThat(result).hasSize(1);
            assertThat(result.get(0).getCategory()).isEqualTo("ROBOT_SAFETY");
        }

        @Test
        @DisplayName("should filter by status")
        void shouldFilterByStatus() {
            ComplianceItem entity1 = createItemEntity("ITEM-001", "CN", "ROBOT_SAFETY", "P0", "COMPLIANT");
            ComplianceItem entity2 = createItemEntity("ITEM-002", "CN", "ROBOT_SAFETY", "P0", "NOT_STARTED");
            when(itemRepo.findByChecklistId(PROJECT_ID)).thenReturn(List.of(entity1, entity2));

            List<ComplianceItem> result = service.getItems(PROJECT_ID, null, "COMPLIANT");

            assertThat(result).hasSize(1);
            assertThat(result.get(0).getStatus()).isEqualTo("COMPLIANT");
        }
    }

    @Nested
    @DisplayName("updateItemStatus")
    class UpdateItemStatus {

        @Test
        @DisplayName("should update item status successfully")
        void shouldUpdateItemStatus() {
            ComplianceItem entity = createItemEntity("ITEM-001", "CN", "ROBOT_SAFETY", "P0", "NOT_STARTED");
            when(itemRepo.findByItemId("ITEM-001")).thenReturn(Optional.of(entity));
            when(itemRepo.save(any(ComplianceItem.class))).thenReturn(entity);

            ComplianceItem result = service.updateItemStatus(PROJECT_ID, "ITEM-001",
                    "COMPLIANT", "test-evidence.pdf", "All checks passed");

            assertThat(result).isNotNull();
            assertThat(result.getStatus()).isEqualTo("COMPLIANT");
            assertThat(result.getEvidence()).isEqualTo("test-evidence.pdf");
            assertThat(result.getNotes()).isEqualTo("All checks passed");
        }

        @Test
        @DisplayName("should return null for non-existent item")
        void shouldReturnNullForNonExistentItem() {
            when(itemRepo.findByItemId("NON-EXISTENT")).thenReturn(Optional.empty());

            ComplianceItem result = service.updateItemStatus(PROJECT_ID, "NON-EXISTENT",
                    "COMPLIANT", null, null);

            assertThat(result).isNull();
            verify(itemRepo, never()).save(any());
        }
    }

    @Nested
    @DisplayName("getProgress")
    class GetProgress {

        @Test
        @DisplayName("should calculate progress correctly")
        void shouldCalculateProgress() {
            ComplianceItem entity1 = createItemEntity("ITEM-001", "CN", "ROBOT_SAFETY", "P0", "COMPLIANT");
            ComplianceItem entity2 = createItemEntity("ITEM-002", "CN", "WIRELESS_EMC", "P0", "IN_PROGRESS");
            ComplianceItem entity3 = createItemEntity("ITEM-003", "CN", "PRIVACY_DATA", "P0", "NOT_STARTED");
            ComplianceItem entity4 = createItemEntity("ITEM-004", "CN", "ROBOT_SAFETY", "P0", "NON_COMPLIANT");
            when(itemRepo.findByChecklistId(PROJECT_ID)).thenReturn(List.of(entity1, entity2, entity3, entity4));

            ProjectProgress result = service.getProgress(PROJECT_ID);

            assertThat(result.total()).isEqualTo(4);
            assertThat(result.compliant()).isEqualTo(1);
            assertThat(result.inProgress()).isEqualTo(1);
            assertThat(result.nonCompliant()).isEqualTo(1);
            assertThat(result.notStarted()).isEqualTo(1);
            assertThat(result.progressPercent()).isEqualTo(25.0);
            assertThat(result.byCategory()).containsKey("ROBOT_SAFETY");
        }

        @Test
        @DisplayName("should handle empty project")
        void shouldHandleEmptyProject() {
            when(itemRepo.findByChecklistId(PROJECT_ID)).thenReturn(List.of());

            ProjectProgress result = service.getProgress(PROJECT_ID);

            assertThat(result.total()).isEqualTo(0);
            assertThat(result.progressPercent()).isEqualTo(0.0);
            assertThat(result.byCategory()).isEmpty();
        }
    }

    @Nested
    @DisplayName("identifyGaps")
    class IdentifyGaps {

        @Test
        @DisplayName("should identify P0/P1 non-compliant gaps")
        void shouldIdentifyGaps() {
            ComplianceItem p0NonCompliant = createItemEntity("ITEM-001", "EU", "ROBOT_SAFETY", "P0", "NON_COMPLIANT");
            ComplianceItem p1InProgress = createItemEntity("ITEM-002", "EU", "WIRELESS_EMC", "P1", "IN_PROGRESS");
            ComplianceItem p0Compliant = createItemEntity("ITEM-003", "EU", "PRIVACY_DATA", "P0", "COMPLIANT");
            ComplianceItem p2NotStarted = createItemEntity("ITEM-004", "EU", "ENVIRONMENTAL", "P2", "NOT_STARTED");
            when(itemRepo.findByChecklistId(PROJECT_ID)).thenReturn(List.of(
                    p0NonCompliant, p1InProgress, p0Compliant, p2NotStarted));

            List<ComplianceItem> gaps = service.identifyGaps(PROJECT_ID, "ALL");

            assertThat(gaps).hasSize(2);
            assertThat(gaps).extracting(ComplianceItem::getPriority).containsOnly("P0", "P1");
        }
    }

    @Nested
    @DisplayName("generateReport")
    class GenerateReport {

        @Test
        @DisplayName("should generate full compliance report")
        void shouldGenerateReport() {
            ComplianceChecklist checklist = new ComplianceChecklist();
            checklist.setChecklistId(PROJECT_ID);
            checklist.setProjectName("Test Project");
            checklist.setTargetMarkets("EU");
            checklist.setStatus("ACTIVE");
            checklist.setCreatedAt(LocalDateTime.now());
            when(checklistRepo.findByChecklistId(PROJECT_ID)).thenReturn(Optional.of(checklist));

            ComplianceItem item = createItemEntity("ITEM-001", "EU", "ROBOT_SAFETY", "P0", "NON_COMPLIANT");
            when(itemRepo.findByChecklistId(PROJECT_ID)).thenReturn(List.of(item));

            ComplianceReport report = service.generateReport(PROJECT_ID);

            assertThat(report).isNotNull();
            assertThat(report.project()).isNotNull();
            assertThat(report.project().name()).isEqualTo("Test Project");
            assertThat(report.progress()).isNotNull();
            assertThat(report.generatedAt()).isNotNull();
        }

        @Test
        @DisplayName("should return null for non-existent project")
        void shouldReturnNullForNonExistentProject() {
            when(checklistRepo.findByChecklistId("NON-EXISTENT")).thenReturn(Optional.empty());

            ComplianceReport report = service.generateReport("NON-EXISTENT");

            assertThat(report).isNull();
        }
    }

    // Helper
    private ComplianceItem createItemEntity(String itemId, String market, String category,
                                             String priority, String status) {
        ComplianceItem entity = new ComplianceItem();
        entity.setItemId(itemId);
        entity.setChecklistId(PROJECT_ID);
        entity.setProjectId(PROJECT_ID);
        entity.setMarket(market);
        entity.setCategory(category);
        entity.setTitle("Test Item");
        entity.setDescription("Test Description");
        entity.setPriority(priority);
        entity.setStatus(status);
        entity.setCreatedAt(LocalDateTime.now());
        entity.setUpdatedAt(LocalDateTime.now());
        return entity;
    }
}
