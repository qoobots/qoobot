package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.entity.DeviceCertificate;
import com.qoobot.qooauth.auth.service.DeviceCertificateService;
import com.qoobot.qooauth.auth.service.DeviceCertificateService.CrlResponse;
import com.qoobot.qooauth.auth.service.DeviceCertificateService.IssuedCertificate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.security.Principal;
import java.util.List;
import java.util.Map;

/**
 * X.509 Device Certificate REST controller.
 *
 * Endpoints:
 *   POST   /api/v1/auth/device-certs/issue              — Issue a new device certificate (from CSR)
 *   POST   /api/v1/auth/device-certs/bootstrap           — Issue bootstrap certificate (initial provisioning)
 *   POST   /api/v1/auth/device-certs/{certId}/renew      — Renew certificate (with new CSR)
 *   DELETE /api/v1/auth/device-certs/{certId}            — Revoke certificate
 *   GET    /api/v1/auth/device-certs/{certId}            — Get certificate details
 *   GET    /api/v1/auth/device-certs                     — List user's certificates
 *   GET    /api/v1/auth/device-certs/device/{deviceId}   — List device's certificates
 *   GET    /api/v1/auth/device-certs/validate/{serial}   — Validate a certificate
 *   GET    /api/v1/auth/device-certs/crl                 — Get CRL (public)
 *   GET    /api/v1/auth/device-certs/crl/delta           — Get delta CRL (public)
 */
@RestController
@RequestMapping("/api/v1/auth/device-certs")
public class DeviceCertificateController {

    private final DeviceCertificateService certService;

    public DeviceCertificateController(DeviceCertificateService certService) {
        this.certService = certService;
    }

    /**
     * Issue a new device certificate from a PKCS#10 CSR.
     */
    @PostMapping("/issue")
    public ResponseEntity<Map<String, Object>> issueCertificate(
            Principal principal,
            @RequestBody IssueRequest request) {
        IssuedCertificate cert = certService.issueCertificate(
                principal.getName(),
                request.deviceId(),
                request.csr(),
                request.metadata(),
                request.validityDays()
        );

        return ResponseEntity.status(HttpStatus.CREATED).body(toCertResponse(cert));
    }

    /**
     * Issue a bootstrap certificate for initial device provisioning.
     * No user binding required — used during device activation.
     */
    @PostMapping("/bootstrap")
    public ResponseEntity<Map<String, Object>> issueBootstrap(
            @RequestBody BootstrapRequest request) {
        IssuedCertificate cert = certService.issueBootstrapCertificate(
                request.deviceId(),
                request.metadata()
        );

        return ResponseEntity.status(HttpStatus.CREATED).body(toCertResponse(cert));
    }

    /**
     * Renew a device certificate with a new CSR.
     */
    @PostMapping("/{certId}/renew")
    public ResponseEntity<Map<String, Object>> renewCertificate(
            Principal principal,
            @PathVariable String certId,
            @RequestBody RenewRequest request) {
        IssuedCertificate cert = certService.renewCertificate(certId, request.csr());

        return ResponseEntity.ok(toCertResponse(cert));
    }

    /**
     * Revoke a device certificate.
     */
    @DeleteMapping("/{certId}")
    public ResponseEntity<Map<String, String>> revokeCertificate(
            Principal principal,
            @PathVariable String certId,
            @RequestBody(required = false) RevokeRequest request) {
        String reason = request != null && request.reason() != null
                ? request.reason() : "cessationOfOperation";
        String invalidityDate = request != null ? request.invalidityDate() : null;

        certService.revokeCertificate(certId, reason,
                invalidityDate != null ? java.time.Instant.parse(invalidityDate) : null);

        return ResponseEntity.ok(Map.of(
                "cert_id", certId,
                "state", "REVOKED",
                "message", "Certificate has been revoked"
        ));
    }

    /**
     * Get certificate details.
     */
    @GetMapping("/{certId}")
    public ResponseEntity<Map<String, Object>> getCertificate(
            Principal principal,
            @PathVariable String certId) {
        DeviceCertificate cert = certService.getCertificate(certId)
                .orElseThrow(() -> new com.qoobot.qooauth.common.exception.AuthException(
                        com.qoobot.qooauth.common.constants.ErrorCodes.NOT_FOUND,
                        "Certificate not found: " + certId));

        return ResponseEntity.ok(toCertDetailResponse(cert));
    }

    /**
     * List certificates owned by the authenticated user.
     */
    @GetMapping
    public ResponseEntity<List<Map<String, Object>>> listUserCertificates(Principal principal) {
        List<DeviceCertificate> certs = certService.listCertificatesByUser(principal.getName());

        List<Map<String, Object>> response = certs.stream()
                .map(this::toCertDetailResponse)
                .toList();

        return ResponseEntity.ok(response);
    }

    /**
     * List certificates for a specific device.
     */
    @GetMapping("/device/{deviceId}")
    public ResponseEntity<List<Map<String, Object>>> listDeviceCertificates(
            Principal principal,
            @PathVariable String deviceId) {
        List<DeviceCertificate> certs = certService.listCertificatesByDevice(deviceId);

        List<Map<String, Object>> response = certs.stream()
                .map(this::toCertDetailResponse)
                .toList();

        return ResponseEntity.ok(response);
    }

    /**
     * Validate a certificate by serial number.
     * Public endpoint — called by API gateway / mTLS verifiers.
     */
    @GetMapping("/validate/{serialNumber}")
    public ResponseEntity<Map<String, Object>> validateCertificate(
            @PathVariable String serialNumber) {
        DeviceCertificate cert = certService.validateCertificate(serialNumber);

        return ResponseEntity.ok(Map.of(
                "valid", true,
                "cert_id", cert.getCertId(),
                "serial_number", cert.getSerialNumber(),
                "subject_dn", cert.getSubjectDn(),
                "device_id", cert.getDeviceId(),
                "user_id", cert.getUserId(),
                "fingerprint_sha256", cert.getFingerprintSha256(),
                "not_before", cert.getNotBefore().toString(),
                "not_after", cert.getNotAfter().toString(),
                "state", cert.getState()
        ));
    }

    /**
     * Get the current Certificate Revocation List.
     * Public endpoint — no authentication required (RFC 5280).
     */
    @GetMapping("/crl")
    public ResponseEntity<Map<String, Object>> getCrl() {
        CrlResponse crl = certService.getCurrentCrl();

        return ResponseEntity.ok(Map.of(
                "crl_number", crl.crlNumber(),
                "next_update", crl.nextUpdate().toString(),
                "revoked_certificates", crl.revokedCertificates()
        ));
    }

    /**
     * Get delta CRL: only entries since a given CRL number.
     * Public endpoint.
     */
    @GetMapping("/crl/delta")
    public ResponseEntity<Map<String, Object>> getDeltaCrl(
            @RequestParam(defaultValue = "0") long sinceCrlNumber) {
        CrlResponse crl = certService.getDeltaCrl(sinceCrlNumber);

        return ResponseEntity.ok(Map.of(
                "crl_number", crl.crlNumber(),
                "next_update", crl.nextUpdate().toString(),
                "delta_from", sinceCrlNumber,
                "revoked_certificates", crl.revokedCertificates()
        ));
    }

    // --- Private helpers ---

    private Map<String, Object> toCertResponse(IssuedCertificate cert) {
        Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("cert_id", cert.certId());
        map.put("serial_number", cert.serialNumber());
        map.put("subject_dn", cert.subjectDn());
        map.put("issuer_dn", cert.issuerDn());
        map.put("certificate_pem", cert.certPem());
        if (cert.keyPem() != null && cert.keyPem().contains("PRIVATE KEY")) {
            map.put("private_key_pem", cert.keyPem());
            map.put("warning", "Store this private key securely. It will not be shown again.");
        }
        map.put("fingerprint_sha256", cert.fingerprintSha256());
        map.put("not_before", cert.notBefore().toString());
        map.put("not_after", cert.notAfter().toString());
        map.put("created_at", cert.createdAt().toString());
        return map;
    }

    private Map<String, Object> toCertDetailResponse(DeviceCertificate cert) {
        Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("cert_id", cert.getCertId());
        map.put("serial_number", cert.getSerialNumber());
        map.put("subject_dn", cert.getSubjectDn());
        map.put("issuer_dn", cert.getIssuerDn());
        map.put("fingerprint_sha256", cert.getFingerprintSha256());
        map.put("key_algorithm", cert.getKeyAlgorithm());
        map.put("state", cert.getState());
        map.put("not_before", cert.getNotBefore().toString());
        map.put("not_after", cert.getNotAfter().toString());
        map.put("auto_renew", cert.getAutoRenew());
        map.put("user_id", cert.getUserId());
        map.put("device_id", cert.getDeviceId());
        map.put("metadata", cert.getMetadata());
        if (cert.getRevocationDate() != null) {
            map.put("revocation_date", cert.getRevocationDate().toString());
            map.put("revocation_reason", cert.getRevocationReason());
        }
        map.put("created_at", cert.getCreatedAt().toString());
        return map;
    }

    // --- Request DTOs ---

    public record IssueRequest(
            String deviceId,
            String csr,
            String metadata,
            Integer validityDays
    ) {}

    public record BootstrapRequest(
            String deviceId,
            String metadata
    ) {}

    public record RenewRequest(
            String csr
    ) {}

    public record RevokeRequest(
            String reason,
            String invalidityDate
    ) {}
}
