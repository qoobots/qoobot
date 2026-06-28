package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "device_ca_config")
public class DeviceCaConfig {

    @Id
    @Column(name = "ca_id", length = 64)
    private String caId;

    @Column(name = "ca_name", nullable = false, length = 128)
    private String caName;

    @Column(name = "ca_cert_pem", nullable = false, columnDefinition = "TEXT")
    private String caCertPem;

    @Column(name = "ca_private_key_enc", nullable = false, columnDefinition = "TEXT")
    private String caPrivateKeyEnc;

    @Column(name = "key_algorithm", nullable = false, length = 16)
    private String keyAlgorithm = "ECDSA_P256";

    @Column(name = "serial_counter", nullable = false)
    private Long serialCounter = 1L;

    @Column(name = "crl_number", nullable = false)
    private Long crlNumber = 0L;

    @Column(name = "default_validity_days", nullable = false)
    private Integer defaultValidityDays = 365;

    @Column(name = "max_validity_days", nullable = false)
    private Integer maxValidityDays = 730;

    @Column(name = "next_crl_update", nullable = false)
    private Instant nextCrlUpdate;

    @Column(name = "crl_update_interval_hours", nullable = false)
    private Integer crlUpdateIntervalHours = 24;

    @Column(nullable = false, length = 16)
    private String state = "ACTIVE";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    // Getters and setters
    public String getCaId() { return caId; }
    public void setCaId(String caId) { this.caId = caId; }

    public String getCaName() { return caName; }
    public void setCaName(String caName) { this.caName = caName; }

    public String getCaCertPem() { return caCertPem; }
    public void setCaCertPem(String caCertPem) { this.caCertPem = caCertPem; }

    public String getCaPrivateKeyEnc() { return caPrivateKeyEnc; }
    public void setCaPrivateKeyEnc(String caPrivateKeyEnc) { this.caPrivateKeyEnc = caPrivateKeyEnc; }

    public String getKeyAlgorithm() { return keyAlgorithm; }
    public void setKeyAlgorithm(String keyAlgorithm) { this.keyAlgorithm = keyAlgorithm; }

    public Long getSerialCounter() { return serialCounter; }
    public void setSerialCounter(Long serialCounter) { this.serialCounter = serialCounter; }

    public Long getCrlNumber() { return crlNumber; }
    public void setCrlNumber(Long crlNumber) { this.crlNumber = crlNumber; }

    public Integer getDefaultValidityDays() { return defaultValidityDays; }
    public void setDefaultValidityDays(Integer defaultValidityDays) { this.defaultValidityDays = defaultValidityDays; }

    public Integer getMaxValidityDays() { return maxValidityDays; }
    public void setMaxValidityDays(Integer maxValidityDays) { this.maxValidityDays = maxValidityDays; }

    public Instant getNextCrlUpdate() { return nextCrlUpdate; }
    public void setNextCrlUpdate(Instant nextCrlUpdate) { this.nextCrlUpdate = nextCrlUpdate; }

    public Integer getCrlUpdateIntervalHours() { return crlUpdateIntervalHours; }
    public void setCrlUpdateIntervalHours(Integer crlUpdateIntervalHours) { this.crlUpdateIntervalHours = crlUpdateIntervalHours; }

    public String getState() { return state; }
    public void setState(String state) { this.state = state; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
