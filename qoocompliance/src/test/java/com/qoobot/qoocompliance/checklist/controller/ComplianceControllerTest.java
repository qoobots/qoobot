package com.qoobot.qoocompliance.checklist.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.qoobot.qoocompliance.aiethics.service.AIEthicsService;
import com.qoobot.qoocompliance.checklist.service.ComplianceChecklistService;
import com.qoobot.qoocompliance.checklist.service.ComplianceChecklistService.*;
import com.qoobot.qoocompliance.consumer.service.ConsumerSafetyService;
import com.qoobot.qoocompliance.environmental.service.EnvironmentalService;
import com.qoobot.qoocompliance.management.service.ComplianceManagementService;
import com.qoobot.qoocompliance.privacy.service.PrivacyDataService;
import com.qoobot.qoocompliance.safety.service.RobotSafetyService;
import com.qoobot.qoocompliance.trade.service.ExportControlService;
import com.qoobot.qoocompliance.wireless.service.WirelessEmcService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.bean.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;
import java.util.List;
import java.util.Map;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(ComplianceController.class)
@DisplayName("ComplianceController")
class ComplianceControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private ComplianceChecklistService checklistService;

    @MockBean
    private RobotSafetyService safetyService;

    @MockBean
    private WirelessEmcService wirelessService;

    @MockBean
    private PrivacyDataService privacyService;

    @MockBean
    private AIEthicsService aiEthicsService;

    @MockBean
    private ConsumerSafetyService consumerService;

    @MockBean
    private ExportControlService exportControlService;

    @MockBean
    private EnvironmentalService environmentalService;

    @MockBean
    private ComplianceManagementService managementService;

    private static final String PROJECT_ID = "test-project-123";

    @Nested
    @DisplayName("POST /api/v1/compliance/checklist")
    class GenerateChecklist {

        @Test
        @DisplayName("should generate checklist and return 200")
        void shouldGenerateChecklist() throws Exception {
            ComplianceProject project = new ComplianceProject(
                    PROJECT_ID, "Test Project", List.of("CN", "EU"), "DRAFT", Instant.now());
            when(checklistService.generateChecklist(anyString(), anyList())).thenReturn(project);

            String body = objectMapper.writeValueAsString(Map.of(
                    "projectName", "Test Project",
                    "targetMarkets", List.of("CN", "EU")
            ));

            mockMvc.perform(post("/api/v1/compliance/checklist")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(body))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.projectId").value(PROJECT_ID))
                    .andExpect(jsonPath("$.name").value("Test Project"))
                    .andExpect(jsonPath("$.targetMarkets[0]").value("CN"))
                    .andExpect(jsonPath("$.targetMarkets[1]").value("EU"));
        }
    }

    @Nested
    @DisplayName("GET /api/v1/compliance/projects/{projectId}/items")
    class GetItems {

        @Test
        @DisplayName("should return items with 200")
        void shouldReturnItems() throws Exception {
            ComplianceItem item = new ComplianceItem("ITEM-001", "CN", "ROBOT_SAFETY",
                    "P0", "Test Item", "Test Description", "NOT_STARTED");
            when(checklistService.getItems(eq(PROJECT_ID), isNull(), isNull()))
                    .thenReturn(List.of(item));

            mockMvc.perform(get("/api/v1/compliance/projects/{projectId}/items", PROJECT_ID))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$[0].itemId").value("ITEM-001"))
                    .andExpect(jsonPath("$[0].category").value("ROBOT_SAFETY"));
        }

        @Test
        @DisplayName("should support category and status query params")
        void shouldSupportFilterParams() throws Exception {
            when(checklistService.getItems(eq(PROJECT_ID), eq("ROBOT_SAFETY"), eq("COMPLIANT")))
                    .thenReturn(List.of());

            mockMvc.perform(get("/api/v1/compliance/projects/{projectId}/items", PROJECT_ID)
                            .param("category", "ROBOT_SAFETY")
                            .param("status", "COMPLIANT"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$").isEmpty());
        }
    }

    @Nested
    @DisplayName("PUT /api/v1/compliance/projects/{projectId}/items/{itemId}")
    class UpdateItem {

        @Test
        @DisplayName("should update item and return 200")
        void shouldUpdateItem() throws Exception {
            ComplianceItem updated = new ComplianceItem("ITEM-001", "CN", "ROBOT_SAFETY",
                    "P0", "Test Item", "Test Description", "COMPLIANT");
            updated.setEvidence("evidence.pdf");
            updated.setNotes("Verified");
            when(checklistService.updateItemStatus(eq(PROJECT_ID), eq("ITEM-001"),
                    eq("COMPLIANT"), eq("evidence.pdf"), eq("Verified")))
                    .thenReturn(updated);

            String body = objectMapper.writeValueAsString(Map.of(
                    "status", "COMPLIANT",
                    "evidence", "evidence.pdf",
                    "notes", "Verified"
            ));

            mockMvc.perform(put("/api/v1/compliance/projects/{projectId}/items/{itemId}",
                            PROJECT_ID, "ITEM-001")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(body))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.status").value("COMPLIANT"))
                    .andExpect(jsonPath("$.evidence").value("evidence.pdf"));
        }

        @Test
        @DisplayName("should return 404 when item not found")
        void shouldReturn404WhenItemNotFound() throws Exception {
            when(checklistService.updateItemStatus(eq(PROJECT_ID), eq("NON-EXISTENT"),
                    anyString(), any(), any())).thenReturn(null);

            String body = objectMapper.writeValueAsString(Map.of("status", "COMPLIANT"));

            mockMvc.perform(put("/api/v1/compliance/projects/{projectId}/items/{itemId}",
                            PROJECT_ID, "NON-EXISTENT")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(body))
                    .andExpect(status().isNotFound());
        }
    }

    @Nested
    @DisplayName("GET /api/v1/compliance/projects/{projectId}/progress")
    class GetProgress {

        @Test
        @DisplayName("should return progress with 200")
        void shouldReturnProgress() throws Exception {
            ProjectProgress progress = new ProjectProgress(
                    PROJECT_ID, 10, 5, 2, 1, 2, 50.0, Map.of());
            when(checklistService.getProgress(PROJECT_ID)).thenReturn(progress);

            mockMvc.perform(get("/api/v1/compliance/projects/{projectId}/progress", PROJECT_ID))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.projectId").value(PROJECT_ID))
                    .andExpect(jsonPath("$.total").value(10))
                    .andExpect(jsonPath("$.compliant").value(5))
                    .andExpect(jsonPath("$.progressPercent").value(50.0));
        }
    }

    @Nested
    @DisplayName("GET /api/v1/compliance/projects/{projectId}/gaps")
    class IdentifyGaps {

        @Test
        @DisplayName("should return gaps with 200")
        void shouldReturnGaps() throws Exception {
            ComplianceItem gap = new ComplianceItem("ITEM-001", "EU", "ROBOT_SAFETY",
                    "P0", "CE MD", "Compliance required", "NON_COMPLIANT");
            when(checklistService.identifyGaps(eq(PROJECT_ID), eq("ALL")))
                    .thenReturn(List.of(gap));

            mockMvc.perform(get("/api/v1/compliance/projects/{projectId}/gaps", PROJECT_ID))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$[0].itemId").value("ITEM-001"))
                    .andExpect(jsonPath("$[0].priority").value("P0"));
        }
    }

    @Nested
    @DisplayName("GET /api/v1/compliance/projects/{projectId}/report")
    class GenerateReport {

        @Test
        @DisplayName("should return report with 200")
        void shouldReturnReport() throws Exception {
            ComplianceProject project = new ComplianceProject(
                    PROJECT_ID, "Test Project", List.of("EU"), "ACTIVE", Instant.now());
            ProjectProgress progress = new ProjectProgress(
                    PROJECT_ID, 10, 8, 1, 0, 1, 80.0, Map.of());
            ComplianceReport report = new ComplianceReport(project, progress, List.of(), Instant.now());
            when(checklistService.generateReport(PROJECT_ID)).thenReturn(report);

            mockMvc.perform(get("/api/v1/compliance/projects/{projectId}/report", PROJECT_ID))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.project.name").value("Test Project"))
                    .andExpect(jsonPath("$.progress.total").value(10));
        }
    }
}
