package com.qoobot.qooauth.device.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

/**
 * Response DTO for certificate information.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CertificateResponse {

    private Long id;
    private String serialNumber;
    private String certType;
    private String subjectCn;
    private String subjectOrg;
    private String deviceId;
    private OffsetDateTime notBefore;
    private OffsetDateTime notAfter;
    private String state;
    private OffsetDateTime revokedAt;
    private String revocationReason;
    private String sha256Fingerprint;
    private OffsetDateTime createdAt;

    /**
     * Create a CertificateResponse from a Certificate entity.
     */
    public static CertificateResponse from(com.qoobot.qooauth.device.entity.Certificate cert) {
        return CertificateResponse.builder()
                .id(cert.getId())
                .serialNumber(cert.getSerialNumber())
                .certType(cert.getCertType())
                .subjectCn(cert.getSubjectCn())
                .subjectOrg(cert.getSubjectOrg())
                .deviceId(cert.getDeviceId())
                .notBefore(cert.getNotBefore())
                .notAfter(cert.getNotAfter())
                .state(cert.getState())
                .revokedAt(cert.getRevokedAt())
                .revocationReason(cert.getRevocationReason())
                .sha256Fingerprint(cert.getSha256Fingerprint())
                .createdAt(cert.getCreatedAt())
                .build();
    }
}
