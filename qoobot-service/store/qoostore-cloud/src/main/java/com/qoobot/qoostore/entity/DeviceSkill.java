package com.qoobot.qoostore.entity;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "device_skills")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DeviceSkill {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "device_id", nullable = false, length = 128)
    private String deviceId;

    @Column(name = "skill_id", nullable = false)
    private Long skillId;

    @Column(name = "version_id")
    private Long versionId;

    @Column(name = "license_id")
    private Long licenseId;

    @Column(length = 16)
    @Builder.Default
    private String status = "installing";

    @Column(name = "installed_at")
    private LocalDateTime installedAt;

    @Column(name = "updated_at")
    @Builder.Default
    private LocalDateTime updatedAt = LocalDateTime.now();

    @PreUpdate
    public void preUpdate() {
        this.updatedAt = LocalDateTime.now();
    }
}
