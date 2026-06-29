package com.qoobot.qooauth.security.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * Privacy label entity representing data collection and usage metadata.
 * Supports GDPR/CCPA/PIPL compliance by cataloging what data is collected,
 * why, and how long it is retained.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "privacy_labels")
public class PrivacyLabel {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * Category of the label (e.g., "PERSONAL", "BEHAVIORAL", "DEVICE", "LOCATION").
     */
    @Column(name = "label_category", nullable = false, length = 64)
    private String labelCategory;

    /**
     * Type of data collected (e.g., "EMAIL", "IP_ADDRESS", "GEOLOCATION", "FINGERPRINT").
     */
    @Column(name = "data_type", nullable = false, length = 64)
    private String dataType;

    /**
     * Purpose of data collection (e.g., "AUTHENTICATION", "ANALYTICS", "SECURITY").
     */
    @Column(name = "collection_purpose", length = 256)
    private String collectionPurpose;

    /**
     * Whether the data collection is optional for the user.
     */
    @Column(name = "is_optional", nullable = false)
    @Builder.Default
    private Boolean isOptional = false;

    /**
     * Data retention period in days. -1 indicates indefinite retention.
     */
    @Column(name = "retention_days", nullable = false)
    @Builder.Default
    private Integer retentionDays = 365;

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();

    @PrePersist
    protected void onCreate() {
        if (createdAt == null) {
            createdAt = Instant.now();
        }
    }
}
