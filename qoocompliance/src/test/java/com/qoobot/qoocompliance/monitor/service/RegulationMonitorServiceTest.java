package com.qoobot.qoocompliance.monitor.service;

import com.qoobot.qoocompliance.domain.Regulation;
import com.qoobot.qoocompliance.domain.RegulationChange;
import com.qoobot.qoocompliance.repository.RegulationChangeRepository;
import com.qoobot.qoocompliance.repository.RegulationRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
@DisplayName("RegulationMonitorService")
class RegulationMonitorServiceTest {

    @Mock
    private RegulationRepository regulationRepo;

    @Mock
    private RegulationChangeRepository changeRepo;

    @InjectMocks
    private RegulationMonitorService service;

    private Regulation gdpr;
    private Regulation aiAct;
    private Regulation pipl;

    @BeforeEach
    void setUp() {
        gdpr = createRegulation("EU-REG-001", "GDPR", "PRIVACY_DATA", "EU", "ACTIVE", "CRITICAL",
                LocalDate.of(2018, 5, 25));
        aiAct = createRegulation("EU-REG-002", "EU AI Act", "AI_ETHICS", "EU", "UPCOMING", "HIGH",
                LocalDate.of(2025, 6, 1));
        pipl = createRegulation("CN-REG-001", "PIPL", "PRIVACY_DATA", "CN", "ACTIVE", "CRITICAL",
                LocalDate.of(2021, 11, 1));
    }

    @Nested
    @DisplayName("getRegulations")
    class GetRegulations {

        @Test
        @DisplayName("should return regulations for a given market")
        void shouldReturnRegulationsForMarket() {
            when(regulationRepo.findByMarket("EU")).thenReturn(List.of(gdpr, aiAct));

            List<RegulationMonitorService.Regulation> result = service.getRegulations("EU");

            assertThat(result).hasSize(2);
            assertThat(result.get(0).getName()).isEqualTo("GDPR");
            assertThat(result.get(1).getName()).isEqualTo("EU AI Act");
        }

        @Test
        @DisplayName("should return empty list for market with no regulations")
        void shouldReturnEmptyForUnknownMarket() {
            when(regulationRepo.findByMarket("JP")).thenReturn(List.of());

            List<RegulationMonitorService.Regulation> result = service.getRegulations("JP");

            assertThat(result).isEmpty();
        }
    }

    @Nested
    @DisplayName("getUpcomingChanges")
    class GetUpcomingChanges {

        @Test
        @DisplayName("should return only upcoming regulations")
        void shouldReturnUpcomingRegulations() {
            when(regulationRepo.findByMarket("EU")).thenReturn(List.of(gdpr, aiAct));

            List<RegulationMonitorService.Regulation> result = service.getUpcomingChanges("EU");

            assertThat(result).hasSize(1);
            assertThat(result.get(0).getName()).isEqualTo("EU AI Act");
            assertThat(result.get(0).getStatus()).isEqualTo("UPCOMING");
        }
    }

    @Nested
    @DisplayName("getChangeHistory")
    class GetChangeHistory {

        @Test
        @DisplayName("should return changes for a given market")
        void shouldReturnChangesForMarket() {
            RegulationChange change1 = new RegulationChange();
            change1.setId(1L);
            change1.setRegulationId("EU-REG-001");
            change1.setMarket("EU");
            change1.setDescription("GDPR update");
            change1.setImpactLevel("HIGH");
            when(changeRepo.findAll()).thenReturn(List.of(change1));
            when(regulationRepo.findByRegulationId("EU-REG-001")).thenReturn(Optional.of(gdpr));

            List<RegulationMonitorService.RegulationChange> result = service.getChangeHistory("EU");

            assertThat(result).hasSize(1);
            assertThat(result.get(0).regulationId()).isEqualTo("EU-REG-001");
            assertThat(result.get(0).description()).isEqualTo("GDPR update");
        }

        @Test
        @DisplayName("should filter out changes from other markets")
        void shouldFilterOtherMarkets() {
            RegulationChange change1 = new RegulationChange();
            change1.setId(1L);
            change1.setRegulationId("EU-REG-001");
            change1.setMarket("EU");
            change1.setDescription("GDPR update");
            change1.setImpactLevel("HIGH");

            RegulationChange change2 = new RegulationChange();
            change2.setId(2L);
            change2.setRegulationId("CN-REG-001");
            change2.setMarket("CN");
            change2.setDescription("PIPL update");
            change2.setImpactLevel("MEDIUM");

            when(changeRepo.findAll()).thenReturn(List.of(change1, change2));
            when(regulationRepo.findByRegulationId("EU-REG-001")).thenReturn(Optional.of(gdpr));
            when(regulationRepo.findByRegulationId("CN-REG-001")).thenReturn(Optional.of(pipl));

            List<RegulationMonitorService.RegulationChange> result = service.getChangeHistory("EU");

            assertThat(result).hasSize(1);
            assertThat(result.get(0).regulationId()).isEqualTo("EU-REG-001");
        }
    }

    @Nested
    @DisplayName("recordChange")
    class RecordChange {

        @Test
        @DisplayName("should save a regulation change record")
        void shouldSaveRegulationChange() {
            service.recordChange("EU", "EU-REG-001", "New amendment", "HIGH");

            verify(changeRepo).save(any(com.qoobot.qoocompliance.domain.RegulationChange.class));
        }
    }

    // Helper
    private Regulation createRegulation(String regulationId, String title, String category,
                                         String market, String status, String impactLevel,
                                         LocalDate effectiveDate) {
        Regulation reg = new Regulation();
        reg.setRegulationId(regulationId);
        reg.setTitle(title);
        reg.setShortName(title);
        reg.setCategory(category);
        reg.setMarket(market);
        reg.setStatus(status);
        reg.setImpactLevel(impactLevel);
        reg.setEffectiveDate(effectiveDate);
        return reg;
    }
}
