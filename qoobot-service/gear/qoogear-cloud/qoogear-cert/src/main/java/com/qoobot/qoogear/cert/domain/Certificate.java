package com.qoobot.qoogear.cert.domain;

import com.qoobot.qoogear.common.entity.BaseEntity;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.time.ZonedDateTime;

@Data
@Entity
@Table(name = "certificates")
@EqualsAndHashCode(callSuper = true)
public class Certificate extends BaseEntity {

    @Column(name = "application_id", nullable = false, unique = true)
    private Long applicationId;

    @Column(name = "cert_number", nullable = false, unique = true, length = 50)
    private String certNumber;

    @Column(name = "cert_level", nullable = false, length = 20)
    private String certLevel;

    @Column(name = "developer_id", nullable = false)
    private Long developerId;

    @Column(name = "product_name", nullable = false, length = 200)
    private String productName;

    @Column(name = "product_model", nullable = false, length = 100)
    private String productModel;

    @Column(name = "product_category", nullable = false, length = 50)
    private String productCategory;

    @Column(name = "issued_at", nullable = false)
    private ZonedDateTime issuedAt;

    @Column(name = "expires_at", nullable = false)
    private ZonedDateTime expiresAt;

    @Column(name = "revoked_at")
    private ZonedDateTime revokedAt;

    @Column(name = "revoke_reason", columnDefinition = "TEXT")
    private String revokeReason;

    @Column(name = "public_key", columnDefinition = "TEXT")
    private String publicKey;

    @Column(name = "cert_doc_url", length = 500)
    private String certDocUrl;

    public boolean isActive() {
        return revokedAt == null
                && expiresAt != null
                && expiresAt.isAfter(ZonedDateTime.now());
    }
}
