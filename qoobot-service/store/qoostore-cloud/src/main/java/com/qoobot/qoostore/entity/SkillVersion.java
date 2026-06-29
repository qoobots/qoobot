package com.qoobot.qoostore.entity;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "skill_versions")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class SkillVersion {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "skill_id", nullable = false)
    private Long skillId;

    @Column(nullable = false, length = 32)
    private String version;

    @Column(columnDefinition = "TEXT")
    private String changelog;

    @Column(name = "package_url", length = 1024)
    private String packageUrl;

    @Column(name = "package_size")
    private Long packageSize;

    @Column(name = "package_hash", length = 128)
    private String packageHash;

    @Column(name = "manifest_json", columnDefinition = "jsonb")
    private String manifestJson;

    @Column(name = "min_qos_version", length = 16)
    private String minQosVersion;

    @Column(name = "privacy_label", columnDefinition = "jsonb")
    private String privacyLabel;

    @Column(name = "permissions", columnDefinition = "text[]")
    private String[] permissions;

    @Column(length = 16)
    @Builder.Default
    private String status = "pending";

    @Column(name = "created_at")
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();
}
