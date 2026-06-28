package com.qoobot.qoocloud.data.entity;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "experience_data", indexes = {
    @Index(name = "idx_device_id", columnList = "deviceId"),
    @Index(name = "idx_experience_type", columnList = "experienceType"),
    @Index(name = "idx_created_at", columnList = "createdAt")
})
public class ExperienceData {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private String id;

    @Column(nullable = false)
    private String deviceId;

    @Column(nullable = false)
    private String experienceType;  // navigation, manipulation, interaction

    @Column(columnDefinition = "TEXT")
    private String payload;         // JSON serialized experience data

    @Column(columnDefinition = "TEXT")
    private String metadata;        // Tags, environment info

    private String checksum;        // SHA-256 for deduplication

    private Double qualityScore;    // Experience quality rating [0, 1]

    private Long fileSizeBytes;

    @Column(nullable = false)
    private Instant createdAt;

    private Instant processedAt;

    private String status;          // pending, processing, stored, discarded

    @PrePersist
    protected void onCreate() {
        if (createdAt == null) createdAt = Instant.now();
        if (status == null) status = "pending";
    }
}
