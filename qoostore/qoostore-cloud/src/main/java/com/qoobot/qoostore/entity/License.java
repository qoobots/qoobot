package com.qoobot.qoostore.entity;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "licenses")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class License {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private UUID userId;

    @Column(name = "skill_id", nullable = false)
    private Long skillId;

    @Column(name = "version_id")
    private Long versionId;

    @Column(name = "order_id")
    private Long orderId;

    @Column(name = "device_id", length = 128)
    private String deviceId;

    @Column(name = "license_key", nullable = false, unique = true, length = 255)
    private String licenseKey;

    @Column(length = 16)
    @Builder.Default
    private String type = "perpetual";

    @Column(length = 16)
    @Builder.Default
    private String status = "active";

    @Column(name = "starts_at")
    private LocalDateTime startsAt;

    @Column(name = "expires_at")
    private LocalDateTime expiresAt;

    @Column(name = "created_at")
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();
}
