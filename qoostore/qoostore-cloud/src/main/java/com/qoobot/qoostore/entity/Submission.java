package com.qoobot.qoostore.entity;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "submissions")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Submission {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "version_id", nullable = false)
    private Long versionId;

    @Column(length = 16)
    @Builder.Default
    private String type = "new";

    @Column(length = 16)
    @Builder.Default
    private String status = "pending";

    @Column(name = "auto_scan_id", length = 64)
    private String autoScanId;

    @Column(name = "scan_result", columnDefinition = "jsonb")
    private String scanResult;

    @Column(name = "reviewer_id")
    private UUID reviewerId;

    @Column(name = "reject_reason", columnDefinition = "TEXT")
    private String rejectReason;

    @Column(name = "reviewed_at")
    private LocalDateTime reviewedAt;

    @Column(name = "created_at")
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    @Builder.Default
    private LocalDateTime updatedAt = LocalDateTime.now();

    @PreUpdate
    public void preUpdate() {
        this.updatedAt = LocalDateTime.now();
    }
}
