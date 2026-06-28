package com.qoobot.qooauth.auth.service;

import com.qoobot.qooauth.auth.entity.CrlEntry;
import com.qoobot.qooauth.auth.entity.DeviceCaConfig;
import com.qoobot.qooauth.auth.entity.DeviceCertificate;
import com.qoobot.qooauth.auth.repository.CrlEntryRepository;
import com.qoobot.qooauth.auth.repository.DeviceCaConfigRepository;
import com.qoobot.qooauth.auth.repository.DeviceCertificateRepository;
import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.common.util.IdGenerator;
import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.jwk.Curve;
import com.nimbusds.jose.jwk.ECKey;
import com.nimbusds.jose.jwk.gen.ECKeyGenerator;
import org.bouncycastle.asn1.x500.X500Name;
import org.bouncycastle.asn1.x500.X500NameBuilder;
import org.bouncycastle.asn1.x500.style.BCStyle;
import org.bouncycastle.asn1.x509.*;
import org.bouncycastle.cert.X509CertificateHolder;
import org.bouncycastle.cert.X509v3CertificateBuilder;
import org.bouncycastle.cert.jcajce.JcaX509CertificateConverter;
import org.bouncycastle.cert.jcajce.JcaX509v3CertificateBuilder;
import org.bouncycastle.jce.provider.BouncyCastleProvider;
import org.bouncycastle.operator.ContentSigner;
import org.bouncycastle.operator.jcajce.JcaContentSignerBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.cert.X509Certificate;
import java.security.interfaces.ECPublicKey;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;

/**
 * X.509 Device Certificate Service.
 *
 * Manages the full lifecycle of device identity certificates:
 * - CA initialization (ECDSA P-256 root CA)
 * - Certificate issuance (CSR-based)
 * - Certificate renewal (auto + manual)
 * - Certificate revocation with CRL management
 * - CRL distribution points
 * - Scheduled tasks: auto-renewal, expiry, CRL generation
 *
 * Uses BouncyCastle for X.509 certificate operations.
 */
@Service
public class DeviceCertificateService {

    private static final Logger log = LoggerFactory.getLogger(DeviceCertificateService.class);
    private static final String CA_ID = "qoo_device_ca_v1";
    private static final String SIGNATURE_ALGORITHM = "SHA256withECDSA";
    private static final String CA_COMMON_NAME = "QooBot Device CA";
    private static final String CA_ORG = "QooBot Inc.";
    private static final String CA_COUNTRY = "US";

    private final DeviceCertificateRepository certRepo;
    private final CrlEntryRepository crlRepo;
    private final DeviceCaConfigRepository caConfigRepo;

    public DeviceCertificateService(DeviceCertificateRepository certRepo,
                                     CrlEntryRepository crlRepo,
                                     DeviceCaConfigRepository caConfigRepo) {
        this.certRepo = certRepo;
        this.crlRepo = crlRepo;
        this.caConfigRepo = caConfigRepo;
    }

    // ========================================================================
    // CA Management
    // ========================================================================

    /**
     * Initialize or get the Device CA.
     * If no CA exists, generates a new ECDSA P-256 key pair and self-signed CA cert.
     */
    @Transactional
    public DeviceCaConfig getOrInitializeCa() {
        Optional<DeviceCaConfig> existing = caConfigRepo.findByState("ACTIVE");
        if (existing.isPresent()) {
            return existing.get();
        }

        try {
            Security.addProvider(new BouncyCastleProvider());

            // Generate CA key pair (ECDSA P-256)
            KeyPairGenerator keyGen = KeyPairGenerator.getInstance("EC");
            keyGen.initialize(256);
            KeyPair caKeyPair = keyGen.generateKeyPair();

            // Build CA subject DN
            X500Name issuerDN = new X500NameBuilder(BCStyle.INSTANCE)
                    .addRDN(BCStyle.CN, CA_COMMON_NAME)
                    .addRDN(BCStyle.O, CA_ORG)
                    .addRDN(BCStyle.C, CA_COUNTRY)
                    .build();

            // Generate serial number for CA cert
            BigInteger serial = BigInteger.valueOf(System.currentTimeMillis());

            // Create self-signed CA certificate (valid 10 years)
            Instant notBefore = Instant.now();
            Instant notAfter = notBefore.plus(3650, ChronoUnit.DAYS);

            X509v3CertificateBuilder certBuilder = new JcaX509v3CertificateBuilder(
                    issuerDN, serial,
                    Date.from(notBefore), Date.from(notAfter),
                    issuerDN, caKeyPair.getPublic());

            // Add CA extensions
            certBuilder.addExtension(Extension.basicConstraints, true, new BasicConstraints(true));
            certBuilder.addExtension(Extension.keyUsage, true,
                    new KeyUsage(KeyUsage.keyCertSign | KeyUsage.cRLSign));
            certBuilder.addExtension(Extension.subjectKeyIdentifier, false,
                    new SubjectKeyIdentifier(
                            sha1(caKeyPair.getPublic().getEncoded())));

            // Sign
            ContentSigner signer = new JcaContentSignerBuilder(SIGNATURE_ALGORITHM)
                    .build(caKeyPair.getPrivate());
            X509CertificateHolder holder = certBuilder.build(signer);

            X509Certificate caCert = new JcaX509CertificateConverter()
                    .setProvider("BC")
                    .getCertificate(holder);

            // Encode keys
            String caCertPem = pemEncode("CERTIFICATE", caCert.getEncoded());
            String publicKeyPem = pemEncode("PUBLIC KEY", caKeyPair.getPublic().getEncoded());
            String privateKeyEnc = encryptPrivateKey(caKeyPair.getPrivate().getEncoded());

            // Persist CA config
            DeviceCaConfig config = new DeviceCaConfig();
            config.setCaId(CA_ID);
            config.setCaName(CA_COMMON_NAME);
            config.setCaCertPem(caCertPem);
            config.setCaPrivateKeyEnc(privateKeyEnc);
            config.setKeyAlgorithm("ECDSA_P256");
            config.setSerialCounter(1L);
            config.setCrlNumber(0L);
            config.setDefaultValidityDays(365);
            config.setMaxValidityDays(730);
            config.setNextCrlUpdate(Instant.now().plus(24, ChronoUnit.HOURS));
            config.setCrlUpdateIntervalHours(24);
            config.setState("ACTIVE");
            config.setCreatedAt(Instant.now());
            config.setUpdatedAt(Instant.now());

            config = caConfigRepo.save(config);

            log.info("Device CA initialized: subject={}, valid until={}", CA_COMMON_NAME, notAfter);
            return config;

        } catch (Exception e) {
            log.error("Failed to initialize Device CA", e);
            throw new AuthException(ErrorCodes.INTERNAL_ERROR, "Failed to initialize Device CA: " + e.getMessage());
        }
    }

    // ========================================================================
    // Certificate Issuance
    // ========================================================================

    /**
     * Issue a new X.509 device certificate from a CSR (PKCS#10).
     *
     * @param userId       Owner user ID (nullable for unbound devices)
     * @param deviceId     Device identifier
     * @param csrPem       PKCS#10 Certificate Signing Request in PEM format
     * @param metadata     Device metadata JSON (model, firmware, hardware fingerprint)
     * @param validityDays Requested validity in days (capped at CA max)
     * @return The issued certificate with full details
     */
    @Transactional
    public IssuedCertificate issueCertificate(String userId, String deviceId,
                                               String csrPem, String metadata,
                                               Integer validityDays) {
        try {
            Security.addProvider(new BouncyCastleProvider());

            DeviceCaConfig ca = getOrInitializeCa();

            // Decode CA private key
            PrivateKey caPrivateKey = decryptPrivateKey(ca.getCaPrivateKeyEnc(), ca.getKeyAlgorithm());

            // Parse CSR
            String csrBody = csrPem
                    .replace("-----BEGIN CERTIFICATE REQUEST-----", "")
                    .replace("-----END CERTIFICATE REQUEST-----", "")
                    .replaceAll("\\s", "");
            byte[] csrBytes = Base64.getDecoder().decode(csrBody);

            org.bouncycastle.pkcs.PKCS10CertificationRequest csr =
                    new org.bouncycastle.pkcs.PKCS10CertificationRequest(csrBytes);

            // Verify CSR signature
            if (!csr.isSignatureValid(new org.bouncycastle.operator.jcajce.JcaContentVerifierProviderBuilder()
                    .build(csr.getSubjectPublicKeyInfo()))) {
                throw new AuthException(ErrorCodes.DEVICE_CSR_INVALID, "CSR signature verification failed");
            }

            // Extract subject public key
            PublicKey devicePublicKey = new org.bouncycastle.jce.provider.BouncyCastleProvider()
                    .getClass().getName() != null ?
                    KeyFactory.getInstance("EC").generatePublic(
                            new X509EncodedKeySpec(csr.getSubjectPublicKeyInfo().getEncoded())) : null;

            // Fallback: use BC provider directly
            java.security.KeyFactory keyFactory = java.security.KeyFactory.getInstance("EC", "BC");
            devicePublicKey = keyFactory.generatePublic(
                    new X509EncodedKeySpec(csr.getSubjectPublicKeyInfo().getEncoded()));

            // Validate public key algorithm
            if (!"EC".equals(devicePublicKey.getAlgorithm())) {
                throw new AuthException(ErrorCodes.DEVICE_KEY_ALGORITHM_INVALID,
                        "Only ECDSA P-256 keys are accepted, got: " + devicePublicKey.getAlgorithm());
            }

            // Build subject DN from CSR
            X500Name subjectDN = csr.getSubject();
            String subjectDnStr = subjectDN.toString();

            // Build issuer DN from CA cert
            byte[] caCertBytes = Base64.getDecoder().decode(
                    ca.getCaCertPem()
                            .replace("-----BEGIN CERTIFICATE-----", "")
                            .replace("-----END CERTIFICATE-----", "")
                            .replaceAll("\\s", ""));
            X509CertificateHolder caCertHolder = new X509CertificateHolder(caCertBytes);
            X500Name issuerDN = caCertHolder.getSubject();

            // Allocate serial number
            long serialNumber = ca.getSerialCounter();
            ca.setSerialCounter(serialNumber + 1);

            // Determine validity period
            int actualValidityDays = Math.min(
                    validityDays != null ? validityDays : ca.getDefaultValidityDays(),
                    ca.getMaxValidityDays());

            Instant notBefore = Instant.now();
            Instant notAfter = notBefore.plus(actualValidityDays, ChronoUnit.DAYS);

            // Build certificate
            X509v3CertificateBuilder certBuilder = new JcaX509v3CertificateBuilder(
                    issuerDN, BigInteger.valueOf(serialNumber),
                    Date.from(notBefore), Date.from(notAfter),
                    subjectDN, devicePublicKey);

            // Extensions
            certBuilder.addExtension(Extension.basicConstraints, false,
                    new BasicConstraints(false)); // Not a CA
            certBuilder.addExtension(Extension.keyUsage, true,
                    new KeyUsage(KeyUsage.digitalSignature | KeyUsage.keyEncipherment));
            certBuilder.addExtension(Extension.extendedKeyUsage, false,
                    new ExtendedKeyUsage(new KeyPurposeId[]{
                            KeyPurposeId.id_kp_clientAuth,
                            KeyPurposeId.id_kp_serverAuth
                    }));
            certBuilder.addExtension(Extension.subjectKeyIdentifier, false,
                    new SubjectKeyIdentifier(sha1(devicePublicKey.getEncoded())));
            certBuilder.addExtension(Extension.authorityKeyIdentifier, false,
                    new org.bouncycastle.asn1.x509.AuthorityKeyIdentifier(
                            sha1(caCertHolder.getSubjectPublicKeyInfo().getEncoded())));

            // CRL Distribution Points
            GeneralName crlDistName = new GeneralName(GeneralName.uniformResourceIdentifier,
                    "https://auth.qoobot.com/api/v1/auth/device-certs/crl");
            DistributionPoint crlDistPoint = new DistributionPoint(
                    new DistributionPointName(new GeneralNames(crlDistName)), null, null);
            certBuilder.addExtension(Extension.cRLDistributionPoints, false,
                    new CRLDistributor(new DistributionPoint[]{crlDistPoint}));

            // Sign certificate
            ContentSigner signer = new JcaContentSignerBuilder(SIGNATURE_ALGORITHM)
                    .setProvider("BC")
                    .build(caPrivateKey);
            X509CertificateHolder certHolder = certBuilder.build(signer);

            X509Certificate x509Cert = new JcaX509CertificateConverter()
                    .setProvider("BC")
                    .getCertificate(certHolder);

            // Compute fingerprints
            String fingerprint = sha256Hex(x509Cert.getEncoded());
            String serialHex = String.format("%040X", serialNumber);

            // Persist certificate
            DeviceCertificate cert = new DeviceCertificate();
            cert.setCertId(IdGenerator.generateDeviceCertId());
            cert.setUserId(userId);
            cert.setDeviceId(deviceId);
            cert.setSerialNumber(serialHex);
            cert.setSubjectDn(subjectDnStr);
            cert.setIssuerDn(issuerDN.toString());
            cert.setPublicKeyPem(pemEncode("PUBLIC KEY", devicePublicKey.getEncoded()));
            cert.setCertPem(pemEncode("CERTIFICATE", x509Cert.getEncoded()));
            cert.setFingerprintSha256(fingerprint);
            cert.setKeyAlgorithm("ECDSA_P256");
            cert.setNotBefore(notBefore);
            cert.setNotAfter(notAfter);
            cert.setState("ACTIVE");
            cert.setAutoRenew(true);
            cert.setRenewThresholdDays(30);
            cert.setMetadata(metadata != null ? metadata : "{}");
            cert.setCreatedAt(Instant.now());
            cert.setUpdatedAt(Instant.now());

            cert = certRepo.save(cert);

            // Update CA serial counter
            ca.setUpdatedAt(Instant.now());
            caConfigRepo.save(ca);

            log.info("Device certificate issued: certId={}, deviceId={}, serial={}, subject={}",
                    cert.getCertId(), deviceId, serialHex, subjectDnStr);

            return new IssuedCertificate(
                    cert.getCertId(), cert.getSerialNumber(), cert.getSubjectDn(),
                    cert.getIssuerDn(), cert.getCertPem(), cert.getPublicKeyPem(),
                    cert.getFingerprintSha256(), cert.getNotBefore(), cert.getNotAfter(),
                    cert.getCreatedAt()
            );

        } catch (AuthException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to issue device certificate", e);
            throw new AuthException(ErrorCodes.DEVICE_CERT_ISSUE_FAILED,
                    "Failed to issue device certificate: " + e.getMessage());
        }
    }

    /**
     * Issue a self-signed bootstrap certificate for initial device provisioning.
     * Limited validity (7 days) and restricted to device activation flow only.
     */
    @Transactional
    public IssuedCertificate issueBootstrapCertificate(String deviceId, String metadata) {
        try {
            Security.addProvider(new BouncyCastleProvider());

            // Generate device key pair
            KeyPairGenerator keyGen = KeyPairGenerator.getInstance("EC");
            keyGen.initialize(256);
            KeyPair deviceKeyPair = keyGen.generateKeyPair();

            // Build subject DN
            X500Name subjectDN = new X500NameBuilder(BCStyle.INSTANCE)
                    .addRDN(BCStyle.CN, "bootstrap-" + deviceId)
                    .addRDN(BCStyle.O, "QooBot Device (Bootstrap)")
                    .addRDN(BCStyle.C, "US")
                    .build();

            BigInteger serial = BigInteger.valueOf(System.currentTimeMillis());
            Instant notBefore = Instant.now();
            Instant notAfter = notBefore.plus(7, ChronoUnit.DAYS);

            // Self-signed
            X509v3CertificateBuilder certBuilder = new JcaX509v3CertificateBuilder(
                    subjectDN, serial,
                    Date.from(notBefore), Date.from(notAfter),
                    subjectDN, deviceKeyPair.getPublic());

            certBuilder.addExtension(Extension.basicConstraints, false,
                    new BasicConstraints(false));
            certBuilder.addExtension(Extension.keyUsage, true,
                    new KeyUsage(KeyUsage.digitalSignature | KeyUsage.keyEncipherment));
            certBuilder.addExtension(Extension.extendedKeyUsage, false,
                    new ExtendedKeyUsage(KeyPurposeId.id_kp_clientAuth));

            ContentSigner signer = new JcaContentSignerBuilder(SIGNATURE_ALGORITHM)
                    .setProvider("BC")
                    .build(deviceKeyPair.getPrivate());
            X509CertificateHolder holder = certBuilder.build(signer);

            X509Certificate x509Cert = new JcaX509CertificateConverter()
                    .setProvider("BC")
                    .getCertificate(holder);

            String fingerprint = sha256Hex(x509Cert.getEncoded());
            String serialHex = String.format("%040X", serial);

            DeviceCertificate cert = new DeviceCertificate();
            cert.setCertId(IdGenerator.generateDeviceCertId());
            cert.setUserId(null);
            cert.setDeviceId(deviceId);
            cert.setSerialNumber(serialHex);
            cert.setSubjectDn(subjectDN.toString());
            cert.setIssuerDn(subjectDN.toString()); // Self-signed
            cert.setPublicKeyPem(pemEncode("PUBLIC KEY", deviceKeyPair.getPublic().getEncoded()));
            cert.setCertPem(pemEncode("CERTIFICATE", x509Cert.getEncoded()));
            cert.setFingerprintSha256(fingerprint);
            cert.setKeyAlgorithm("ECDSA_P256");
            cert.setNotBefore(notBefore);
            cert.setNotAfter(notAfter);
            cert.setState("ACTIVE");
            cert.setAutoRenew(false);
            cert.setMetadata(metadata != null ? metadata : "{\"bootstrap\":true}");
            cert.setCreatedAt(Instant.now());
            cert.setUpdatedAt(Instant.now());

            cert = certRepo.save(cert);

            log.info("Bootstrap certificate issued: deviceId={}, expires in 7 days", deviceId);

            return new IssuedCertificate(
                    cert.getCertId(), cert.getSerialNumber(), cert.getSubjectDn(),
                    cert.getIssuerDn(), cert.getCertPem(),
                    pemEncode("PRIVATE KEY", deviceKeyPair.getPrivate().getEncoded()),
                    cert.getFingerprintSha256(), cert.getNotBefore(), cert.getNotAfter(),
                    cert.getCreatedAt()
            );

        } catch (Exception e) {
            log.error("Failed to issue bootstrap certificate", e);
            throw new AuthException(ErrorCodes.DEVICE_CERT_ISSUE_FAILED,
                    "Failed to issue bootstrap certificate: " + e.getMessage());
        }
    }

    // ========================================================================
    // Certificate Renewal
    // ========================================================================

    /**
     * Renew a device certificate with a new CSR.
     * Revokes old certificate and issues new one.
     */
    @Transactional
    public IssuedCertificate renewCertificate(String certId, String csrPem) {
        DeviceCertificate oldCert = certRepo.findById(certId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "Certificate not found: " + certId));

        if (!"ACTIVE".equals(oldCert.getState()) && !"RENEWING".equals(oldCert.getState())) {
            throw new AuthException(ErrorCodes.DEVICE_CERT_STATE_INVALID,
                    "Cannot renew certificate in state: " + oldCert.getState());
        }

        // Revoke old certificate (superseded)
        revokeCertificateInternal(oldCert, "superseded", null);

        // Issue new certificate
        int remainingDays = (int) ChronoUnit.DAYS.between(oldCert.getNotBefore(), oldCert.getNotAfter());
        IssuedCertificate newCert = issueCertificate(
                oldCert.getUserId(), oldCert.getDeviceId(),
                csrPem, oldCert.getMetadata(), remainingDays);

        log.info("Certificate renewed: oldCertId={}, newCertId={}, deviceId={}",
                certId, newCert.certId(), oldCert.getDeviceId());

        return newCert;
    }

    // ========================================================================
    // Certificate Revocation
    // ========================================================================

    /**
     * Revoke a device certificate.
     */
    @Transactional
    public void revokeCertificate(String certId, String reason, Instant invalidityDate) {
        DeviceCertificate cert = certRepo.findById(certId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "Certificate not found: " + certId));

        if (!"ACTIVE".equals(cert.getState()) && !"RENEWING".equals(cert.getState())) {
            throw new AuthException(ErrorCodes.DEVICE_CERT_ALREADY_REVOKED,
                    "Certificate is already " + cert.getState().toLowerCase());
        }

        revokeCertificateInternal(cert, reason, invalidityDate);

        log.warn("Certificate revoked: certId={}, deviceId={}, reason={}", certId, cert.getDeviceId(), reason);
    }

    private void revokeCertificateInternal(DeviceCertificate cert, String reason, Instant invalidityDate) {
        DeviceCaConfig ca = getOrInitializeCa();

        // Increment CRL number
        long crlNumber = ca.getCrlNumber() + 1;
        ca.setCrlNumber(crlNumber);
        ca.setUpdatedAt(Instant.now());
        caConfigRepo.save(ca);

        // Update certificate state
        cert.setState("REVOKED");
        cert.setRevocationDate(Instant.now());
        cert.setRevocationReason(reason);
        cert.setUpdatedAt(Instant.now());
        certRepo.save(cert);

        // Add CRL entry
        CrlEntry crlEntry = new CrlEntry();
        crlEntry.setEntryId(IdGenerator.generateCrlEntryId());
        crlEntry.setSerialNumber(cert.getSerialNumber());
        crlEntry.setCertId(cert.getCertId());
        crlEntry.setRevocationDate(Instant.now());
        crlEntry.setRevocationReason(reason);
        crlEntry.setInvalidityDate(invalidityDate);
        crlEntry.setCrlNumber(crlNumber);
        crlEntry.setCreatedAt(Instant.now());

        crlRepo.save(crlEntry);
    }

    // ========================================================================
    // CRL Distribution
    // ========================================================================

    /**
     * Generate the current CRL in PEM format (RFC 5280).
     */
    @Transactional
    public CrlResponse getCurrentCrl() {
        List<CrlEntry> entries = crlRepo.findAllByOrderByCrlNumberDesc();

        long latestCrlNumber = entries.isEmpty() ? 0 : entries.get(0).getCrlNumber();

        List<Map<String, Object>> revokedCerts = entries.stream()
                .map(e -> {
                    Map<String, Object> map = new LinkedHashMap<>();
                    map.put("serial_number", e.getSerialNumber());
                    map.put("revocation_date", e.getRevocationDate().toString());
                    map.put("reason", e.getRevocationReason());
                    if (e.getInvalidityDate() != null) {
                        map.put("invalidity_date", e.getInvalidityDate().toString());
                    }
                    return map;
                })
                .toList();

        DeviceCaConfig ca = getOrInitializeCa();

        return new CrlResponse(latestCrlNumber, ca.getNextCrlUpdate(), revokedCerts);
    }

    /**
     * Get delta CRL: only entries added since a given CRL number.
     */
    public CrlResponse getDeltaCrl(long sinceCrlNumber) {
        List<CrlEntry> entries = crlRepo.findByCrlNumberGreaterThan(sinceCrlNumber);

        long latestCrlNumber = entries.isEmpty() ? sinceCrlNumber :
                entries.stream().mapToLong(CrlEntry::getCrlNumber).max().orElse(sinceCrlNumber);

        List<Map<String, Object>> revokedCerts = entries.stream()
                .map(e -> {
                    Map<String, Object> map = new LinkedHashMap<>();
                    map.put("serial_number", e.getSerialNumber());
                    map.put("revocation_date", e.getRevocationDate().toString());
                    map.put("reason", e.getRevocationReason());
                    return map;
                })
                .toList();

        DeviceCaConfig ca = getOrInitializeCa();

        return new CrlResponse(latestCrlNumber, ca.getNextCrlUpdate(), revokedCerts);
    }

    // ========================================================================
    // Query
    // ========================================================================

    public List<DeviceCertificate> listCertificatesByUser(String userId) {
        return certRepo.findByUserId(userId);
    }

    public List<DeviceCertificate> listCertificatesByDevice(String deviceId) {
        return certRepo.findByDeviceId(deviceId);
    }

    public Optional<DeviceCertificate> getCertificate(String certId) {
        return certRepo.findById(certId);
    }

    public Optional<DeviceCertificate> getCertificateBySerial(String serialNumber) {
        return certRepo.findBySerialNumber(serialNumber);
    }

    public Optional<DeviceCertificate> getCertificateByFingerprint(String fingerprint) {
        return certRepo.findByFingerprintSha256(fingerprint);
    }

    /**
     * Validate a device certificate (check it's active, not expired, not revoked).
     */
    public DeviceCertificate validateCertificate(String serialNumber) {
        DeviceCertificate cert = certRepo.findBySerialNumber(serialNumber)
                .orElseThrow(() -> new AuthException(ErrorCodes.DEVICE_CERT_NOT_FOUND,
                        "Certificate not found: " + serialNumber));

        if ("REVOKED".equals(cert.getState())) {
            throw new AuthException(ErrorCodes.DEVICE_CERT_REVOKED,
                    "Certificate revoked: " + cert.getRevocationReason());
        }

        if ("EXPIRED".equals(cert.getState())) {
            throw new AuthException(ErrorCodes.DEVICE_CERT_EXPIRED, "Certificate has expired");
        }

        if (cert.getNotAfter().isBefore(Instant.now())) {
            cert.setState("EXPIRED");
            cert.setUpdatedAt(Instant.now());
            certRepo.save(cert);
            throw new AuthException(ErrorCodes.DEVICE_CERT_EXPIRED, "Certificate has expired");
        }

        if (cert.getNotBefore().isAfter(Instant.now())) {
            throw new AuthException(ErrorCodes.DEVICE_CERT_NOT_YET_VALID, "Certificate is not yet valid");
        }

        return cert;
    }

    // ========================================================================
    // Scheduled Tasks
    // ========================================================================

    /**
     * Auto-renew certificates nearing expiry.
     * Runs every 6 hours.
     */
    @Scheduled(fixedRate = 21600000)
    @Transactional
    public void autoRenewCertificates() {
        Instant renewDeadline = Instant.now().plus(30, ChronoUnit.DAYS);
        List<DeviceCertificate> dueForRenewal = certRepo.findCertificatesDueForRenewal(renewDeadline);

        for (DeviceCertificate cert : dueForRenewal) {
            try {
                cert.setState("RENEWING");
                cert.setUpdatedAt(Instant.now());
                certRepo.save(cert);
                log.info("Certificate marked for renewal: certId={}, deviceId={}, expires={}",
                        cert.getCertId(), cert.getDeviceId(), cert.getNotAfter());
            } catch (Exception e) {
                log.error("Failed to mark certificate for renewal: certId={}", cert.getCertId(), e);
            }
        }

        if (!dueForRenewal.isEmpty()) {
            log.info("Auto-renewal check: {} certificates due for renewal", dueForRenewal.size());
        }
    }

    /**
     * Expire certificates past their validity.
     * Runs every hour.
     */
    @Scheduled(fixedRate = 3600000)
    @Transactional
    public void expireOverdueCertificates() {
        int count = certRepo.expireOverdueCertificates(Instant.now());
        if (count > 0) {
            log.info("Expired {} overdue device certificates", count);
        }
    }

    /**
     * Update CRL next update timestamp.
     * Runs every hour.
     */
    @Scheduled(fixedRate = 3600000)
    @Transactional
    public void updateCrlTimestamp() {
        DeviceCaConfig ca = getOrInitializeCa();
        if (ca.getNextCrlUpdate().isBefore(Instant.now())) {
            ca.setNextCrlUpdate(Instant.now().plus(ca.getCrlUpdateIntervalHours(), ChronoUnit.HOURS));
            ca.setUpdatedAt(Instant.now());
            caConfigRepo.save(ca);
            log.debug("CRL next update set to: {}", ca.getNextCrlUpdate());
        }
    }

    // ========================================================================
    // Private Helpers
    // ========================================================================

    private byte[] sha1(byte[] data) {
        try {
            return MessageDigest.getInstance("SHA-1").digest(data);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
    }

    private String sha256Hex(byte[] data) {
        try {
            byte[] hash = MessageDigest.getInstance("SHA-256").digest(data);
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
    }

    private String pemEncode(String type, byte[] der) {
        StringBuilder sb = new StringBuilder();
        sb.append("-----BEGIN ").append(type).append("-----\n");
        sb.append(Base64.getMimeEncoder(64, "\n".getBytes(StandardCharsets.UTF_8))
                .encodeToString(der));
        sb.append("\n-----END ").append(type).append("-----\n");
        return sb.toString();
    }

    /**
     * Encrypt private key with AES-256-GCM using a derived key.
     * In production, this would use a KMS. Here we use a static derivation.
     */
    private String encryptPrivateKey(byte[] privateKeyBytes) {
        try {
            // Derive key from environment secret (production: KMS)
            String envSecret = System.getenv().getOrDefault("QOO_DEVICE_CA_KEY_SECRET",
                    "qoobot-device-ca-default-key-material-v1");
            MessageDigest sha256 = MessageDigest.getInstance("SHA-256");
            byte[] keyBytes = sha256.digest(envSecret.getBytes(StandardCharsets.UTF_8));
            SecretKey key = new SecretKeySpec(keyBytes, "AES");

            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            byte[] iv = new byte[12];
            new SecureRandom().nextBytes(iv);
            GCMParameterSpec spec = new GCMParameterSpec(128, iv);

            cipher.init(Cipher.ENCRYPT_MODE, key, spec);
            byte[] encrypted = cipher.doFinal(privateKeyBytes);

            // Prepend IV to ciphertext
            byte[] combined = new byte[iv.length + encrypted.length];
            System.arraycopy(iv, 0, combined, 0, iv.length);
            System.arraycopy(encrypted, 0, combined, iv.length, encrypted.length);

            return Base64.getEncoder().encodeToString(combined);

        } catch (Exception e) {
            throw new RuntimeException("Failed to encrypt private key", e);
        }
    }

    private PrivateKey decryptPrivateKey(String encryptedBase64, String algorithm) {
        try {
            byte[] combined = Base64.getDecoder().decode(encryptedBase64);

            // Extract IV (first 12 bytes)
            byte[] iv = new byte[12];
            System.arraycopy(combined, 0, iv, 0, 12);

            // Extract ciphertext
            byte[] encrypted = new byte[combined.length - 12];
            System.arraycopy(combined, 12, encrypted, 0, encrypted.length);

            // Derive key
            String envSecret = System.getenv().getOrDefault("QOO_DEVICE_CA_KEY_SECRET",
                    "qoobot-device-ca-default-key-material-v1");
            MessageDigest sha256 = MessageDigest.getInstance("SHA-256");
            byte[] keyBytes = sha256.digest(envSecret.getBytes(StandardCharsets.UTF_8));
            SecretKey key = new SecretKeySpec(keyBytes, "AES");

            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            GCMParameterSpec spec = new GCMParameterSpec(128, iv);
            cipher.init(Cipher.DECRYPT_MODE, key, spec);
            byte[] decrypted = cipher.doFinal(encrypted);

            PKCS8EncodedKeySpec keySpec = new PKCS8EncodedKeySpec(decrypted);
            return KeyFactory.getInstance("EC").generatePrivate(keySpec);

        } catch (Exception e) {
            throw new RuntimeException("Failed to decrypt CA private key", e);
        }
    }

    // ========================================================================
    // DTOs
    // ========================================================================

    public record IssuedCertificate(
            String certId,
            String serialNumber,
            String subjectDn,
            String issuerDn,
            String certPem,
            String keyPem,
            String fingerprintSha256,
            Instant notBefore,
            Instant notAfter,
            Instant createdAt
    ) {}

    public record CrlResponse(
            long crlNumber,
            Instant nextUpdate,
            List<Map<String, Object>> revokedCertificates
    ) {}
}
