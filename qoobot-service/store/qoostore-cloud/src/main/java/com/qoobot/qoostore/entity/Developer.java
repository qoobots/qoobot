package com.qoobot.qoostore.entity;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "developers")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Developer {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false, unique = true)
    private UUID userId;

    @Column(nullable = false, unique = true, length = 64)
    private String username;

    @Column(name = "display_name", length = 128)
    private String displayName;

    @Column(nullable = false, length = 255)
    private String email;

    @Column(length = 255)
    private String company;

    @Column(length = 512)
    private String website;

    @Column(nullable = false)
    @Builder.Default
    private Boolean verified = false;

    @Column(name = "tax_id", length = 64)
    private String taxId;

    @Column(name = "payout_method", length = 32)
    private String payoutMethod;

    @Column(name = "payout_account", length = 512)
    private String payoutAccount;

    @Column(length = 16)
    @Builder.Default
    private String status = "active";

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
