package com.qoobot.qooauth.auth.entity;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "crl_entries")
public class CrlEntry {

    @Id
    @Column(name = "entry_id", length = 64)
    private String entryId;

    @Column(name = "serial_number", nullable = false, length = 40)
    private String serialNumber;

    @Column(name = "cert_id", length = 64)
    private String certId;

    @Column(name = "revocation_date", nullable = false)
    private Instant revocationDate;

    @Column(name = "revocation_reason", nullable = false, length = 128)
    private String revocationReason;

    @Column(name = "invalidity_date")
    private Instant invalidityDate;

    @Column(name = "crl_number", nullable = false)
    private Long crlNumber;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    // Getters and setters
    public String getEntryId() { return entryId; }
    public void setEntryId(String entryId) { this.entryId = entryId; }

    public String getSerialNumber() { return serialNumber; }
    public void setSerialNumber(String serialNumber) { this.serialNumber = serialNumber; }

    public String getCertId() { return certId; }
    public void setCertId(String certId) { this.certId = certId; }

    public Instant getRevocationDate() { return revocationDate; }
    public void setRevocationDate(Instant revocationDate) { this.revocationDate = revocationDate; }

    public String getRevocationReason() { return revocationReason; }
    public void setRevocationReason(String revocationReason) { this.revocationReason = revocationReason; }

    public Instant getInvalidityDate() { return invalidityDate; }
    public void setInvalidityDate(Instant invalidityDate) { this.invalidityDate = invalidityDate; }

    public Long getCrlNumber() { return crlNumber; }
    public void setCrlNumber(Long crlNumber) { this.crlNumber = crlNumber; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
}
