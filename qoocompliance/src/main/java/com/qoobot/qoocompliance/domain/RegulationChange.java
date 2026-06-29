package com.qoobot.qoocompliance.domain;

import jakarta.persistence.*;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "regulation_change", indexes = {
    @Index(name = "idx_reg_change_regulation_id", columnList = "regulationId"),
    @Index(name = "idx_reg_change_change_type", columnList = "changeType"),
    @Index(name = "idx_reg_change_impact_level", columnList = "impactLevel"),
    @Index(name = "idx_reg_change_effective_date", columnList = "effectiveDate")
})
public class RegulationChange {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 64)
    private String regulationId;

    @Column(length = 32)
    private String changeType;

    @Column(length = 255)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    private LocalDate effectiveDate;

    @Column(length = 32)
    private String impactLevel;

    @Column(columnDefinition = "TEXT")
    private String affectedProducts;

    @Column(nullable = false)
    private Boolean notified = false;

    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        this.createdAt = LocalDateTime.now();
    }

    // --- Getters and Setters ---

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getRegulationId() {
        return regulationId;
    }

    public void setRegulationId(String regulationId) {
        this.regulationId = regulationId;
    }

    public String getChangeType() {
        return changeType;
    }

    public void setChangeType(String changeType) {
        this.changeType = changeType;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public LocalDate getEffectiveDate() {
        return effectiveDate;
    }

    public void setEffectiveDate(LocalDate effectiveDate) {
        this.effectiveDate = effectiveDate;
    }

    public String getImpactLevel() {
        return impactLevel;
    }

    public void setImpactLevel(String impactLevel) {
        this.impactLevel = impactLevel;
    }

    public String getAffectedProducts() {
        return affectedProducts;
    }

    public void setAffectedProducts(String affectedProducts) {
        this.affectedProducts = affectedProducts;
    }

    public Boolean getNotified() {
        return notified;
    }

    public void setNotified(Boolean notified) {
        this.notified = notified;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }
}
