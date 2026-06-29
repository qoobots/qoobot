package com.qoobot.qoocompliance.repository;

import com.qoobot.qoocompliance.domain.Regulation;
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
@DisplayName("RegulationRepository")
class RegulationRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private RegulationRepository repository;

    private Regulation gdpr;
    private Regulation pipl;

    @BeforeEach
    void setUp() {
        gdpr = new Regulation();
        gdpr.setRegulationId("EU-REG-001");
        gdpr.setTitle("General Data Protection Regulation");
        gdpr.setShortName("GDPR");
        gdpr.setCategory("PRIVACY_DATA");
        gdpr.setMarket("EU");
        gdpr.setAuthority("European Commission");
        gdpr.setStatus("ACTIVE");
        gdpr.setImpactLevel("CRITICAL");
        gdpr.setEffectiveDate(LocalDate.of(2018, 5, 25));
        entityManager.persist(gdpr);

        pipl = new Regulation();
        pipl.setRegulationId("CN-REG-001");
        pipl.setTitle("Personal Information Protection Law");
        pipl.setShortName("PIPL");
        pipl.setCategory("PRIVACY_DATA");
        pipl.setMarket("CN");
        pipl.setAuthority("NPC Standing Committee");
        pipl.setStatus("ACTIVE");
        pipl.setImpactLevel("CRITICAL");
        pipl.setEffectiveDate(LocalDate.of(2021, 11, 1));
        entityManager.persist(pipl);

        entityManager.flush();
    }

    @Nested
    @DisplayName("findByRegulationId")
    class FindByRegulationId {

        @Test
        @DisplayName("should find existing regulation by regulationId")
        void shouldFindExistingRegulation() {
            Optional<Regulation> result = repository.findByRegulationId("EU-REG-001");
            assertThat(result).isPresent();
            assertThat(result.get().getTitle()).isEqualTo("General Data Protection Regulation");
        }

        @Test
        @DisplayName("should return empty for non-existent regulationId")
        void shouldReturnEmptyForNonExistent() {
            Optional<Regulation> result = repository.findByRegulationId("NON-EXISTENT");
            assertThat(result).isEmpty();
        }
    }

    @Nested
    @DisplayName("findByMarket")
    class FindByMarket {

        @Test
        @DisplayName("should find regulations by market EU")
        void shouldFindByMarketEU() {
            List<Regulation> result = repository.findByMarket("EU");
            assertThat(result).hasSize(1);
            assertThat(result.get(0).getShortName()).isEqualTo("GDPR");
        }

        @Test
        @DisplayName("should find regulations by market CN")
        void shouldFindByMarketCN() {
            List<Regulation> result = repository.findByMarket("CN");
            assertThat(result).hasSize(1);
            assertThat(result.get(0).getShortName()).isEqualTo("PIPL");
        }

        @Test
        @DisplayName("should return empty for unknown market")
        void shouldReturnEmptyForUnknownMarket() {
            List<Regulation> result = repository.findByMarket("JP");
            assertThat(result).isEmpty();
        }
    }

    @Nested
    @DisplayName("findByCategory")
    class FindByCategory {

        @Test
        @DisplayName("should find regulations by category")
        void shouldFindByCategory() {
            List<Regulation> result = repository.findByCategory("PRIVACY_DATA");
            assertThat(result).hasSize(2);
        }
    }

    @Nested
    @DisplayName("findByStatus")
    class FindByStatus {

        @Test
        @DisplayName("should find active regulations")
        void shouldFindActiveRegulations() {
            List<Regulation> result = repository.findByStatus("ACTIVE");
            assertThat(result).hasSize(2);
        }
    }

    @Nested
    @DisplayName("findByMarketAndCategory")
    class FindByMarketAndCategory {

        @Test
        @DisplayName("should find by market and category")
        void shouldFindByMarketAndCategory() {
            List<Regulation> result = repository.findByMarketAndCategory("EU", "PRIVACY_DATA");
            assertThat(result).hasSize(1);
            assertThat(result.get(0).getShortName()).isEqualTo("GDPR");
        }
    }

    @Nested
    @DisplayName("findByMarketAndStatus")
    class FindByMarketAndStatus {

        @Test
        @DisplayName("should find by market and status")
        void shouldFindByMarketAndStatus() {
            List<Regulation> result = repository.findByMarketAndStatus("CN", "ACTIVE");
            assertThat(result).hasSize(1);
            assertThat(result.get(0).getShortName()).isEqualTo("PIPL");
        }
    }

    @Test
    @DisplayName("should auto-populate createdAt and updatedAt via @PrePersist")
    void shouldAutoPopulateTimestamps() {
        Regulation saved = repository.findById(gdpr.getId()).orElseThrow();
        assertThat(saved.getCreatedAt()).isNotNull();
        assertThat(saved.getUpdatedAt()).isNotNull();
    }
}
