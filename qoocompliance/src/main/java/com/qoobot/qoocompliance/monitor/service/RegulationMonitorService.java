package com.qoobot.qoocompliance.monitor.service;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;

/**
 * Regulation change monitoring service.
 * Tracks regulatory changes across target markets and triggers
 * gap analysis when regulations are updated.
 */
@Service
public class RegulationMonitorService {

    private final Map<String, List<Regulation>> regulations = new HashMap<>();
    private final Map<String, List<RegulationChange>> changeLog = new HashMap<>();

    public RegulationMonitorService() {
        initializeRegulations();
    }

    /**
     * Get all tracked regulations for a market.
     */
    public List<Regulation> getRegulations(String market) {
        return regulations.getOrDefault(market, Collections.emptyList());
    }

    /**
     * Get regulation change history.
     */
    public List<RegulationChange> getChangeHistory(String market) {
        return changeLog.getOrDefault(market, Collections.emptyList());
    }

    /**
     * Record a regulation change.
     */
    public void recordChange(String market, String regulationId, String changeDescription,
                              String severity) {
        RegulationChange change = new RegulationChange(
                UUID.randomUUID().toString(), market, regulationId,
                changeDescription, severity, Instant.now()
        );

        changeLog.computeIfAbsent(market, k -> new ArrayList<>()).add(change);
    }

    /**
     * Get upcoming regulation changes (effective in the future).
     */
    public List<Regulation> getUpcomingChanges(String market) {
        return regulations.getOrDefault(market, Collections.emptyList()).stream()
                .filter(r -> r.getNextUpdateDate() != null &&
                        r.getNextUpdateDate().isAfter(Instant.now()))
                .toList();
    }

    private void initializeRegulations() {
        // China regulations
        List<Regulation> cn = new ArrayList<>();
        cn.add(new Regulation("CN-PIPL", "个人信息保护法", "PIPL",
                Instant.parse("2021-11-01T00:00:00Z"), null, "ACTIVE", "HIGH"));
        cn.add(new Regulation("CN-DSL", "数据安全法", "DSL",
                Instant.parse("2021-09-01T00:00:00Z"), null, "ACTIVE", "HIGH"));
        cn.add(new Regulation("CN-GENAI", "生成式AI服务管理规定",
                "AI Regulation",
                Instant.parse("2023-08-15T00:00:00Z"), null, "ACTIVE", "MEDIUM"));
        regulations.put("CN", cn);

        // EU regulations
        List<Regulation> eu = new ArrayList<>();
        eu.add(new Regulation("EU-GDPR", "通用数据保护条例", "GDPR",
                Instant.parse("2018-05-25T00:00:00Z"), null, "ACTIVE", "HIGH"));
        eu.add(new Regulation("EU-AI-ACT", "人工智能法案", "EU AI Act",
                Instant.parse("2024-08-01T00:00:00Z"),
                Instant.parse("2026-08-02T00:00:00Z"), "ACTIVE", "CRITICAL"));
        eu.add(new Regulation("EU-MDR", "机械法规", "EU 2023/1230",
                Instant.parse("2027-01-20T00:00:00Z"), null, "UPCOMING", "HIGH"));
        regulations.put("EU", eu);

        // US regulations
        List<Regulation> us = new ArrayList<>();
        us.add(new Regulation("US-CCPA", "加州消费者隐私法案", "CCPA/CPRA",
                Instant.parse("2020-01-01T00:00:00Z"), null, "ACTIVE", "MEDIUM"));
        regulations.put("US", us);

        // Japan regulations
        List<Regulation> jp = new ArrayList<>();
        jp.add(new Regulation("JP-APPI", "个人信息保护法", "APPI",
                Instant.parse("2022-04-01T00:00:00Z"), null, "ACTIVE", "MEDIUM"));
        regulations.put("JP", jp);
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
