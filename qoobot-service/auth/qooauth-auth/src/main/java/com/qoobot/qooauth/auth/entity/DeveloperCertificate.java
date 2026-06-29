package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * Developer Certificate — Apple Developer Program style certificate.
 * Used for code signing, skill packaging, and developer identity.
 *
 * Issued to verified developers. Supports:
 * - Development (sandbox only)
 * - Distribution (production skill publishing)
 * - Enterprise (internal distribution)
 */
@Entity
@Table(name = "developer_certificates", indexes = {
    @Index(name = "idx_dc_user", columnList = "userId"),
    @Index(name = "idx_dc_serial", columnList = "serialNumber"),
    @Index(name = "idx_dc_state", columnList = "state")
})
public class DeveloperCertificate {

    @Id
    @Column(name = "cert_id", length = 64)
    private String certId;

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    /**
     * Certificate type: DEVELOPMENT, DISTRIBUTION, ENTERPRISE
     */
    @Column(name = "cert_type", nullable = false, length = 16)
    private String certType;

    /**
     * X.509 serial number (hex)
     */
    @Column(name = "serial_number", nullable = false, length = 64, unique = true)
    private String serialNumber;

    @Column(name = "subject_dn", nullable = false, length = 256)
    private String subjectDn;

    @Column(name = "public_key_pem", nullable = false, columnDefinition = "TEXT")
    private String publicKeyPem;

    @Column(name = "cert_pem", nullable = false, columnDefinition = "TEXT")
    private String certPem;

    @Column(name = "fingerprint_sha256", nullable = false, length = 128)
    private String fingerprintSha256;

    @Column(name = "key_algorithm", nullable = false, length = 16)
    private String keyAlgorithm = "ECDSA_P256";

    @Column(name = "not_before", nullable = false)
    private Instant notBefore;

    @Column(name = "not_after", nullable = false)
    private Instant notAfter;

    /**
     * Certificate state: ACTIVE, REVOKED, EXPIRED
     */
    @Column(name = "state", nullable = false, length = 16)
    private String state = "ACTIVE";

    /**
     * Associated developer team/org ID
     */
    @Column(name = "team_id", length = 64)
    private String teamId;

    /**
     * Capabilities enabled for this certificate as JSON:
     * ["skill_signing", "sandbox_access", "api_access", "beta_testing"]
     */
    @Column(name = "capabilities", columnDefinition = "TEXT")
    private String capabilities;

    @Column(name = "revoked_at")
    private Instant revokedAt;

    @Column(name = "revoke_reason", length = 256)
    private String revokeReason;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    // --- Getters and Setters ---

    public String getCertId() { return certId; }
    public void setCertId(String certId) { this.certId = certId; }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getCertType() { return certType; }
    public void setCertType(String certType) { this.certType = certType; }

    public String getSerialNumber() { return serialNumber; }
    public void setSerialNumber(String serialNumber) { this.serialNumber = serialNumber; }

    public String getSubjectDn() { return subjectDn; }
    public void setSubjectDn(String subjectDn) { this.subjectDn = subjectDn; }

    public String getPublicKeyPem() { return publicKeyPem; }
    public void setPublicKeyPem(String publicKeyPem) { this.publicKeyPem = publicKeyPem; }

    public String getCertPem() { return certPem; }
    public void setCertPem(String certPem) { this.certPem = certPem; }

    public String getFingerprintSha256() { return fingerprintSha256; }
    public void setFingerprintSha256(String fingerprintSha256) { this.fingerprintSha256 = fingerprintSha256; }

    public String getKeyAlgorithm() { return keyAlgorithm; }
    public void setKeyAlgorithm(String keyAlgorithm) { this.keyAlgorithm = keyAlgorithm; }

    public Instant getNotBefore() { return notBefore; }
    public void setNotBefore(Instant notBefore) { this.notBefore = notBefore; }

    public Instant getNotAfter() { return notAfter; }
    public void setNotAfter(Instant notAfter) { this.notAfter = notAfter; }

    public String getState() { return state; }
    public void setState(String state) { this.state = state; }

    public String getTeamId() { return teamId; }
    public void setTeamId(String teamId) { this.teamId = teamId; }

    public String getCapabilities() { return capabilities; }
    public void setCapabilities(String capabilities) { this.capabilities = capabilities; }

    public Instant getRevokedAt() { return revokedAt; }
    public void setRevokedAt(Instant revokedAt) { this.revokedAt = revokedAt; }

    public String getRevokeReason() { return revokeReason; }
    public void setRevokeReason(String revokeReason) { this.revokeReason = revokeReason; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
