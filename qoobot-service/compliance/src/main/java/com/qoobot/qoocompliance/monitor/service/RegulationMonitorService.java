package com.qoobot.qoocompliance.monitor.service;

import com.qoobot.qoocompliance.domain.RegulationChange;
import com.qoobot.qoocompliance.domain.Regulation;
import com.qoobot.qoocompliance.repository.RegulationChangeRepository;
import com.qoobot.qoocompliance.repository.RegulationRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Collections;
import java.util.List;

/**
 * Regulation change monitoring service.
 * Tracks regulatory changes across target markets and triggers
 * gap analysis when regulations are updated.
 */
@Service
public class RegulationMonitorService {

    private final RegulationRepository regulationRepo;
    private final RegulationChangeRepository changeRepo;

    public RegulationMonitorService(RegulationRepository regulationRepo,
                                     RegulationChangeRepository changeRepo) {
        this.regulationRepo = regulationRepo;
        this.changeRepo = changeRepo;
    }

    /**
     * Get all tracked regulations for a market.
     */
    public List<Regulation> getRegulations(String market) {
        return regulationRepo.findByMarket(market).stream()
                .map(this::toDto)
                .toList();
    }

    /**
     * Get regulation change history.
     */
    public List<RegulationChange> getChangeHistory(String market) {
        // Find all changes, filter by checking each regulation's market
        List<com.qoobot.qoocompliance.domain.RegulationChange> allChanges = changeRepo.findAll();
        return allChanges.stream()
                .filter(change -> {
                    Regulation reg = regulationRepo.findByRegulationId(change.getRegulationId()).orElse(null);
                    return reg != null && market.equals(reg.getMarket());
                })
                .map(this::toDto)
                .toList();
    }

    /**
     * Record a regulation change.
     */
    @Transactional
    public void recordChange(String market, String regulationId, String changeDescription,
                              String severity) {
        com.qoobot.qoocompliance.domain.RegulationChange entity =
                new com.qoobot.qoocompliance.domain.RegulationChange();
        entity.setRegulationId(regulationId);
        entity.setMarket(market);
        entity.setChangeType("UPDATE");
        entity.setDescription(changeDescription);
        entity.setImpactLevel(severity);
        entity.setNotified(false);
        changeRepo.save(entity);
    }

    /**
     * Get upcoming regulation changes (effective in the future).
     */
    public List<Regulation> getUpcomingChanges(String market) {
        return regulationRepo.findByMarket(market).stream()
                .filter(r -> "UPCOMING".equals(r.getStatus()))
                .map(this::toDto)
                .toList();
    }

    // --- Conversion methods ---

    private Regulation toDto(com.qoobot.qoocompliance.domain.Regulation entity) {
        Regulation dto = new Regulation();
        dto.setId(entity.getRegulationId());
        dto.setName(entity.getTitle());
        dto.setCategory(entity.getShortName());
        dto.setEffectiveDate(entity.getEffectiveDate() != null
                ? entity.getEffectiveDate().atStartOfDay().toInstant(ZoneOffset.UTC)
                : null);
        dto.setNextUpdateDate(null);
        dto.setStatus(entity.getStatus());
        dto.setImpactLevel(entity.getImpactLevel());
        return dto;
    }

    private RegulationChange toDto(com.qoobot.qoocompliance.domain.RegulationChange entity) {
        return new RegulationChange(
                entity.getId().toString(),
                entity.getMarket(),
                entity.getRegulationId(),
                entity.getDescription(),
                entity.getImpactLevel(),
                entity.getCreatedAt() != null
                        ? entity.getCreatedAt().toInstant(ZoneOffset.UTC)
                        : null
        );
    }

    // --- DTOs ---

    public static class Regulation {
        private String id;
        private String name;
        private String category;
        private Instant effectiveDate;
        private Instant nextUpdateDate;
        private String status;
        private String impactLevel;

        public Regulation() {}

        public Regulation(String id, String name, String category, Instant effectiveDate,
                          Instant nextUpdateDate, String status, String impactLevel) {
            this.id = id;
            this.name = name;
            this.category = category;
            this.effectiveDate = effectiveDate;
            this.nextUpdateDate = nextUpdateDate;
            this.status = status;
            this.impactLevel = impactLevel;
        }

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getCategory() { return category; }
        public void setCategory(String category) { this.category = category; }
        public Instant getEffectiveDate() { return effectiveDate; }
        public void setEffectiveDate(Instant effectiveDate) { this.effectiveDate = effectiveDate; }
        public Instant getNextUpdateDate() { return nextUpdateDate; }
        public void setNextUpdateDate(Instant nextUpdateDate) { this.nextUpdateDate = nextUpdateDate; }
        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }
        public String getImpactLevel() { return impactLevel; }
        public void setImpactLevel(String impactLevel) { this.impactLevel = impactLevel; }
    }

    public record RegulationChange(
            String changeId, String market, String regulationId,
            String description, String severity, Instant recordedAt
    ) {}
}
