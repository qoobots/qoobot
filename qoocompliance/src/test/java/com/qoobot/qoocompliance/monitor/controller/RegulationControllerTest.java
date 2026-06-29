package com.qoobot.qoocompliance.monitor.controller;

import com.qoobot.qoocompliance.monitor.service.RegulationMonitorService;
import com.qoobot.qoocompliance.monitor.service.RegulationMonitorService.*;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.bean.MockBean;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;
import java.util.List;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(RegulationController.class)
@DisplayName("RegulationController")
class RegulationControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private RegulationMonitorService monitorService;

    @Nested
    @DisplayName("GET /api/v1/regulations/{market}")
    class GetRegulations {

        @Test
        @DisplayName("should return regulations for market")
        void shouldReturnRegulations() throws Exception {
            Regulation reg = new Regulation("GDPR", "General Data Protection Regulation",
                    "PRIVACY_DATA", Instant.parse("2018-05-25T00:00:00Z"),
                    null, "ACTIVE", "CRITICAL");
            when(monitorService.getRegulations(eq("EU"))).thenReturn(List.of(reg));

            mockMvc.perform(get("/api/v1/regulations/{market}", "EU"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$[0].id").value("GDPR"))
                    .andExpect(jsonPath("$[0].name").value("General Data Protection Regulation"))
                    .andExpect(jsonPath("$[0].status").value("ACTIVE"));
        }

        @Test
        @DisplayName("should return empty list for unknown market")
        void shouldReturnEmptyForUnknownMarket() throws Exception {
            when(monitorService.getRegulations(eq("JP"))).thenReturn(List.of());

            mockMvc.perform(get("/api/v1/regulations/{market}", "JP"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$").isEmpty());
        }
    }

    @Nested
    @DisplayName("GET /api/v1/regulations/{market}/upcoming")
    class GetUpcomingChanges {

        @Test
        @DisplayName("should return upcoming regulations")
        void shouldReturnUpcomingRegulations() throws Exception {
            Regulation reg = new Regulation("EU-AI-ACT", "EU AI Act",
                    "AI_ETHICS", Instant.parse("2025-06-01T00:00:00Z"),
                    null, "UPCOMING", "HIGH");
            when(monitorService.getUpcomingChanges(eq("EU"))).thenReturn(List.of(reg));

            mockMvc.perform(get("/api/v1/regulations/{market}/upcoming", "EU"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$[0].id").value("EU-AI-ACT"))
                    .andExpect(jsonPath("$[0].status").value("UPCOMING"));
        }
    }

    @Nested
    @DisplayName("GET /api/v1/regulations/{market}/changes")
    class GetChangeHistory {

        @Test
        @DisplayName("should return change history")
        void shouldReturnChangeHistory() throws Exception {
            RegulationChange change = new RegulationChange(
                    "1", "EU", "GDPR", "New data transfer rules", "HIGH", Instant.now());
            when(monitorService.getChangeHistory(eq("EU"))).thenReturn(List.of(change));

            mockMvc.perform(get("/api/v1/regulations/{market}/changes", "EU"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$[0].changeId").value("1"))
                    .andExpect(jsonPath("$[0].market").value("EU"))
                    .andExpect(jsonPath("$[0].regulationId").value("GDPR"))
                    .andExpect(jsonPath("$[0].severity").value("HIGH"));
        }
    }
}
