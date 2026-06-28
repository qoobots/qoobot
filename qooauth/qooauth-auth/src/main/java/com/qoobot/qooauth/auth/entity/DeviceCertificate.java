package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "device_certificates")
public class DeviceCertificate {

    @Id
    @Column(name = "cert_id", length = 64)
    private String certId;

    @Column(name = "user_id", length = 32)
    private String userId;

    @Column(name = "device_id", nullable = false, length = 64)
    private String deviceId;

    @Column(name = "serial_number", nullable = false, unique = true, length = 40)
    private String serialNumber;

    @Column(name = "subject_dn", nullable = false, length = 512)
    private String subjectDn;

    @Column(name = "issuer_dn", nullable = false, length = 512)
    private String issuerDn;

    @Column(name = "public_key_pem", nullable = false, columnDefinition = "TEXT")
    private String publicKeyPem;

    @Column(name = "cert_pem", nullable = false, columnDefinition = "TEXT")
    private String certPem;

    @Column(name = "fingerprint_sha256", nullable = false, unique = true, length = 64)
    private String fingerprintSha256;

    @Column(name = "key_algorithm", nullable = false, length = 16)
    private String keyAlgorithm = "ECDSA_P256";

    @Column(name = "not_before", nullable = false)
    private Instant notBefore;

    @Column(name = "not_after", nullable = false)
    private Instant notAfter;

    @Column(nullable = false, length = 16)
    private String state = "ACTIVE";

    @Column(name = "revocation_date")
    private Instant revocationDate;

    @Column(name = "revocation_reason", length = 128)
    private String revocationReason;

    @Column(name = "auto_renew")
    private Boolean autoRenew = true;

    @Column(name = "renew_threshold_days")
    private Integer renewThresholdDays = 30;

    @Column(columnDefinition = "jsonb")
    private String metadata;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    // Getters and setters
    public String getCertId() { return certId; }
    public void setCertId(String certId) { this.certId = certId; }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getDeviceId() { return deviceId; }
    public void setDeviceId(String deviceId) { this.deviceId = deviceId; }

    public String getSerialNumber() { return serialNumber; }
    public void setSerialNumber(String serialNumber) { this.serialNumber = serialNumber; }

    public String getSubjectDn() { return subjectDn; }
    public void setSubjectDn(String subjectDn) { this.subjectDn = subjectDn; }

    public String getIssuerDn() { return issuerDn; }
    public void setIssuerDn(String issuerDn) { this.issuerDn = issuerDn; }

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

    public Instant getRevocationDate() { return revocationDate; }
    public void setRevocationDate(Instant revocationDate) { this.revocationDate = revocationDate; }

    public String getRevocationReason() { return revocationReason; }
    public void setRevocationReason(String revocationReason) { this.revocationReason = revocationReason; }

    public Boolean getAutoRenew() { return autoRenew; }
    public void setAutoRenew(Boolean autoRenew) { this.autoRenew = autoRenew; }

    public Integer getRenewThresholdDays() { return renewThresholdDays; }
    public void setRenewThresholdDays(Integer renewThresholdDays) { this.renewThresholdDays = renewThresholdDays; }

    public String getMetadata() { return metadata; }
    public void setMetadata(String metadata) { this.metadata = metadata; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
