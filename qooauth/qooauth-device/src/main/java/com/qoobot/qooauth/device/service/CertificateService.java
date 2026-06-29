package com.qoobot.qooauth.device.service;

import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.device.config.CertificateConfig;
import com.qoobot.qooauth.device.entity.Certificate;
import com.qoobot.qooauth.device.repository.CertificateRepository;
import org.bouncycastle.asn1.x500.X500Name;
import org.bouncycastle.asn1.x509.*;
import org.bouncycastle.cert.X509CertificateHolder;
import org.bouncycastle.cert.X509v3CertificateBuilder;
import org.bouncycastle.cert.jcajce.JcaX509CertificateConverter;
import org.bouncycastle.cert.jcajce.JcaX509v3CertificateBuilder;
import org.bouncycastle.jce.provider.BouncyCastleProvider;
import org.bouncycastle.operator.ContentSigner;
import org.bouncycastle.operator.jcajce.JcaContentSignerBuilder;
import org.bouncycastle.pkcs.PKCS10CertificationRequest;
import org.bouncycastle.pkcs.jcajce.JcaPKCS10CertificationRequestBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.FileReader;
import java.io.StringReader;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.cert.X509Certificate;
import java.security.spec.PKCS8EncodedKeySpec;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.*;
import java.util.stream.Collectors;

/**
 * X.509 ECDSA P-256 certificate issuance, renewal, revocation, and CRL generation.
 * <p>
 * Uses BouncyCastle APIs to sign device certificates from a local CA key pair
 * or an HSM-backed key.  All issued certificates are tracked in the
 * {@code certificates} table.
 */
@Service
@Transactional
public class CertificateService {

    private static final Logger log = LoggerFactory.getLogger(CertificateService.class);

    private final CertificateRepository certificateRepository;
    private final CertificateConfig.CaProperties caProperties;
    private final SecureRandom secureRandom;

    private volatile PrivateKey caPrivateKey;
    private volatile X509Certificate caCertificate;

    public CertificateService(CertificateRepository certificateRepository,
                              CertificateConfig.CaProperties caProperties) {
        this.certificateRepository = certificateRepository;
        this.caProperties = caProperties;
        this.secureRandom = new SecureRandom();
    }

    // ========================================================================
    //  Certificate issuance
    // ========================================================================

    /**
     * Issue a new device certificate from a PKCS#10 CSR.
     *
     * @param csrPem    PKCS#10 CSR in PEM format
     * @param deviceId  the device ID this certificate is issued to
     * @param deviceSerial the device serial for the subject CN
     * @return the issued certificate as PEM string
     */
    public String issueDeviceCertificate(String csrPem, String deviceId, String deviceSerial) {
        try {
            PKCS10CertificationRequest csr = parseCsr(csrPem);
            verifyCsr(csr);

            String serialNumber = generateSerialNumber();
            String subjectCn = caProperties.getSubjectDnPattern()
                    .replace("{serial}", deviceSerial);

            X509Certificate deviceCert = buildAndSignCertificate(csr, serialNumber, subjectCn);

            String certPem = toPemString(deviceCert);
            String fingerprint = computeSha256Fingerprint(deviceCert);

            // Persist the certificate record
            Certificate cert = Certificate.builder()
                    .serialNumber(serialNumber)
                    .certType(Certificate.CERT_TYPE_DEVICE)
                    .subjectCn(subjectCn)
                    .subjectOrg("QooBot")
                    .deviceId(deviceId)
                    .notBefore(OffsetDateTime.ofInstant(deviceCert.getNotBefore().toInstant(), ZoneOffset.UTC))
                    .notAfter(OffsetDateTime.ofInstant(deviceCert.getNotAfter().toInstant(), ZoneOffset.UTC))
                    .state(Certificate.STATE_ACTIVE)
                    .sha256Fingerprint(fingerprint)
                    .build();

            certificateRepository.save(cert);
            log.info("Issued device certificate: serial={}, deviceId={}, fingerprint={}",
                    serialNumber, deviceId, fingerprint);

            return certPem;

        } catch (AuthException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to issue device certificate for device {}", deviceId, e);
            throw new AuthException(ErrorCodes.DEVICE_CERT_ISSUE_FAILED,
                    "Certificate issuance failed: " + e.getMessage(), e);
        }
    }

    /**
     * Issue a self-signed CA root certificate (for bootstrap/testing).
     */
    public X509Certificate issueCaCertificate(String subjectCn) {
        try {
            KeyPairGenerator keyGen = KeyPairGenerator.getInstance("EC", BouncyCastleProvider.PROVIDER_NAME);
            keyGen.initialize(256, secureRandom);
            KeyPair caKeyPair = keyGen.generateKeyPair();

            X500Name issuer = new X500Name("CN=" + subjectCn + ",O=QooBot,OU=Device CA");
            X500Name subject = issuer;

            BigInteger serial = BigInteger.valueOf(System.currentTimeMillis());
            Instant notBefore = Instant.now();
            Instant notAfter = notBefore.plus(caProperties.getCertValidity());

            X509v3CertificateBuilder builder = new JcaX509v3CertificateBuilder(
                    issuer, serial, Date.from(notBefore), Date.from(notAfter), subject, caKeyPair.getPublic());

            builder.addExtension(Extension.basicConstraints, true, new BasicConstraints(true));
            builder.addExtension(Extension.keyUsage, true,
                    new KeyUsage(KeyUsage.keyCertSign | KeyUsage.cRLSign));

            ContentSigner signer = new JcaContentSignerBuilder(caProperties.getSignatureAlgorithm())
                    .setProvider(BouncyCastleProvider.PROVIDER_NAME)
                    .build(caKeyPair.getPrivate());

            X509CertificateHolder holder = builder.build(signer);
            return new JcaX509CertificateConverter()
                    .setProvider(BouncyCastleProvider.PROVIDER_NAME)
                    .getCertificate(holder);

        } catch (Exception e) {
            log.error("Failed to issue CA certificate", e);
            throw new AuthException(ErrorCodes.DEVICE_CERT_ISSUE_FAILED,
                    "CA certificate issuance failed: " + e.getMessage(), e);
        }
    }

    // ========================================================================
    //  Certificate renewal
    // ========================================================================

    /**
     * Renew a device certificate. Revokes the old one and issues a new one
     * with a fresh serial number.
     *
     * @param oldSerialNumber the serial number of the certificate to renew
     * @param newCsrPem       a fresh PKCS#10 CSR from the device
     * @param deviceId        the device ID
     * @param deviceSerial    the device serial for the subject CN
     * @return the renewed certificate as PEM string
     */
    public String renewCertificate(String oldSerialNumber, String newCsrPem, String deviceId, String deviceSerial) {
        Certificate oldCert = certificateRepository.findBySerialNumber(oldSerialNumber)
                .orElseThrow(() -> new AuthException(ErrorCodes.DEVICE_CERT_NOT_FOUND,
                        "Certificate not found: " + oldSerialNumber));

        // Revoke the old certificate
        revokeCertificate(oldSerialNumber, "Renewed — superseded by new certificate");

        // Issue a new one
        return issueDeviceCertificate(newCsrPem, deviceId, deviceSerial);
    }

    // ========================================================================
    //  Certificate revocation
    // ========================================================================

    /**
     * Revoke a certificate.
     *
     * @param serialNumber the certificate serial number
     * @param reason       human-readable revocation reason
     */
    public void revokeCertificate(String serialNumber, String reason) {
        OffsetDateTime now = OffsetDateTime.now();
        int updated = certificateRepository.revokeBySerialNumber(serialNumber, now, reason);
        if (updated == 0) {
            throw new AuthException(ErrorCodes.DEVICE_CERT_NOT_FOUND,
                    "Certificate not found or already revoked: " + serialNumber);
        }
        log.info("Revoked certificate: serial={}, reason={}", serialNumber, reason);
    }

    /**
     * Revoke all active certificates for a device (e.g. on device wipe).
     */
    public void revokeAllForDevice(String deviceId, String reason) {
        List<Certificate> certs = certificateRepository.findByDeviceIdAndState(deviceId, Certificate.STATE_ACTIVE);
        for (Certificate cert : certs) {
            revokeCertificate(cert.getSerialNumber(), reason);
        }
        log.info("Revoked {} certificates for device {}", certs.size(), deviceId);
    }

    // ========================================================================
    //  CRL generation
    // ========================================================================

    /**
     * Generate a Certificate Revocation List (CRL) containing all revoked certificates.
     *
     * @return DER-encoded CRL bytes
     */
    public byte[] generateCrl() {
        try {
            List<Certificate> revokedCerts = certificateRepository.findByState(Certificate.STATE_REVOKED);
            if (revokedCerts.isEmpty()) {
                log.debug("No revoked certificates — generating empty CRL");
            }

            // Build a simple CRL using BouncyCastle
            X509Certificate caCert = loadCaCertificate();
            PrivateKey caKey = loadCaPrivateKey();

            X500Name issuer = new X500Name(caCert.getSubjectX500Principal().getName());
            Date now = new Date();
            Date nextUpdate = Date.from(Instant.now().plus(java.time.Duration.ofDays(1)));

            org.bouncycastle.cert.X509CRLHolder crlHolder = buildCrl(issuer, caKey, now, nextUpdate, revokedCerts);

            log.info("Generated CRL with {} revoked certificates", revokedCerts.size());
            return crlHolder.getEncoded();

        } catch (Exception e) {
            log.error("Failed to generate CRL", e);
            throw new AuthException(ErrorCodes.INTERNAL_ERROR,
                    "CRL generation failed: " + e.getMessage(), e);
        }
    }

    // ========================================================================
    //  Certificate queries
    // ========================================================================

    public Optional<Certificate> findBySerialNumber(String serialNumber) {
        return certificateRepository.findBySerialNumber(serialNumber);
    }

    public List<Certificate> findByDeviceId(String deviceId) {
        return certificateRepository.findByDeviceId(deviceId);
    }

    public Optional<Certificate> findActiveByDeviceId(String deviceId) {
        return certificateRepository.findActiveByDeviceId(deviceId);
    }

    public List<Certificate> findAllValid() {
        return certificateRepository.findAllValid(OffsetDateTime.now());
    }

    /**
     * Scheduled task: mark expired certificates as EXPIRED state.
     */
    public void expireStaleCertificates() {
        OffsetDateTime now = OffsetDateTime.now();
        List<Certificate> expired = certificateRepository.findExpiredButActive(now);
        for (Certificate cert : expired) {
            cert.setState(Certificate.STATE_EXPIRED);
            certificateRepository.save(cert);
        }
        if (!expired.isEmpty()) {
            log.info("Expired {} stale certificates", expired.size());
        }
    }

    // ========================================================================
    //  Internal helpers
    // ========================================================================

    private PKCS10CertificationRequest parseCsr(String csrPem) throws Exception {
        String pem = csrPem.replaceAll("-----(BEGIN|END) (NEW )?CERTIFICATE REQUEST-----", "").replaceAll("\\s", "");
        byte[] der = Base64.getDecoder().decode(pem);
        return new PKCS10CertificationRequest(der);
    }

    private void verifyCsr(PKCS10CertificationRequest csr) {
        if (!csr.isSignatureValid()) {
            throw new AuthException(ErrorCodes.DEVICE_CSR_INVALID, "CSR signature verification failed");
        }

        // Verify the public key algorithm is ECDSA
        String algo = csr.getSubjectPublicKeyInfo().getAlgorithm().getAlgorithm().getId();
        if (!algo.contains("ec") && !algo.contains("1.2.840.10045")) {
            log.warn("CSR uses non-EC algorithm: {}", algo);
            // We accept it but log a warning — policy can be tightened later
        }
    }

    private String generateSerialNumber() {
        return String.format("%040d", new BigInteger(160, secureRandom));
    }

    private X509Certificate buildAndSignCertificate(PKCS10CertificationRequest csr,
                                                     String serialNumber,
                                                     String subjectCn) throws Exception {
        X509Certificate caCert = loadCaCertificate();
        PrivateKey caKey = loadCaPrivateKey();

        X500Name issuer = new X500Name(caCert.getSubjectX500Principal().getName());
        X500Name subject = new X500Name(subjectCn);

        BigInteger serial = new BigInteger(serialNumber);
        Instant notBefore = Instant.now();
        Instant notAfter = notBefore.plus(caProperties.getCertValidity());

        X509v3CertificateBuilder builder = new JcaX509v3CertificateBuilder(
                issuer, serial, Date.from(notBefore), Date.from(notAfter),
                subject, csr.getSubjectPublicKeyInfo());

        // Extensions
        builder.addExtension(Extension.basicConstraints, false, new BasicConstraints(false));
        builder.addExtension(Extension.keyUsage, true,
                new KeyUsage(KeyUsage.digitalSignature | KeyUsage.keyEncipherment));
        builder.addExtension(Extension.extendedKeyUsage, true,
                new ExtendedKeyUsage(new KeyPurposeId[]{KeyPurposeId.id_kp_clientAuth, KeyPurposeId.id_kp_serverAuth}));

        // Subject Key Identifier
        byte[] subjectKeyId = computeSubjectKeyIdentifier(csr.getSubjectPublicKeyInfo());
        builder.addExtension(Extension.subjectKeyIdentifier, false,
                new SubjectKeyIdentifier(subjectKeyId));

        ContentSigner signer = new JcaContentSignerBuilder(caProperties.getSignatureAlgorithm())
                .setProvider(BouncyCastleProvider.PROVIDER_NAME)
                .build(caKey);

        X509CertificateHolder holder = builder.build(signer);
        return new JcaX509CertificateConverter()
                .setProvider(BouncyCastleProvider.PROVIDER_NAME)
                .getCertificate(holder);
    }

    private byte[] computeSubjectKeyIdentifier(SubjectPublicKeyInfo spki) throws Exception {
        byte[] keyBytes = spki.getPublicKeyData().getBytes();
        MessageDigest md = MessageDigest.getInstance("SHA-1");
        return md.digest(keyBytes);
    }

    private X509Certificate loadCaCertificate() throws Exception {
        if (caCertificate != null) {
            return caCertificate;
        }
        synchronized (this) {
            if (caCertificate != null) return caCertificate;
            try (FileReader reader = new FileReader(caProperties.getCertPath(), StandardCharsets.UTF_8)) {
                java.security.cert.CertificateFactory cf = java.security.cert.CertificateFactory.getInstance("X.509");
                caCertificate = (X509Certificate) cf.generateCertificate(reader);
                log.info("Loaded CA certificate from {}", caProperties.getCertPath());
                return caCertificate;
            }
        }
    }

    private PrivateKey loadCaPrivateKey() throws Exception {
        if (caPrivateKey != null) {
            return caPrivateKey;
        }
        synchronized (this) {
            if (caPrivateKey != null) return caPrivateKey;

            // If HSM is configured, load via HSM provider
            if (caProperties.getHsmProvider() != null && caProperties.getHsmKeyAlias() != null) {
                KeyStore ks = KeyStore.getInstance("PKCS11", caProperties.getHsmProvider());
                ks.load(null, null);
                caPrivateKey = (PrivateKey) ks.getKey(caProperties.getHsmKeyAlias(), null);
                log.info("Loaded CA private key from HSM alias {}", caProperties.getHsmKeyAlias());
                return caPrivateKey;
            }

            // Otherwise load from PEM file
            String pem = readPemFile(caProperties.getKeyPath());
            byte[] der = Base64.getDecoder().decode(pem);
            PKCS8EncodedKeySpec spec = new PKCS8EncodedKeySpec(der);
            KeyFactory kf = KeyFactory.getInstance("EC", BouncyCastleProvider.PROVIDER_NAME);
            caPrivateKey = kf.generatePrivate(spec);
            log.info("Loaded CA private key from {}", caProperties.getKeyPath());
            return caPrivateKey;
        }
    }

    private String readPemFile(String path) throws Exception {
        StringBuilder sb = new StringBuilder();
        try (FileReader reader = new FileReader(path, StandardCharsets.UTF_8)) {
            char[] buf = new char[4096];
            int n;
            while ((n = reader.read(buf)) != -1) {
                sb.append(buf, 0, n);
            }
        }
        return sb.toString()
                .replaceAll("-----(BEGIN|END) (EC )?PRIVATE KEY-----", "")
                .replaceAll("\\s", "");
    }

    private String computeSha256Fingerprint(X509Certificate cert) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        byte[] digest = md.digest(cert.getEncoded());
        StringBuilder sb = new StringBuilder();
        for (byte b : digest) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    private String toPemString(X509Certificate cert) throws Exception {
        StringBuilder sb = new StringBuilder();
        sb.append("-----BEGIN CERTIFICATE-----\n");
        sb.append(Base64.getMimeEncoder(64, "\n".getBytes(StandardCharsets.UTF_8))
                .encodeToString(cert.getEncoded()));
        sb.append("\n-----END CERTIFICATE-----\n");
        return sb.toString();
    }

    @SuppressWarnings("deprecation")
    private org.bouncycastle.cert.X509CRLHolder buildCrl(
            X500Name issuer, PrivateKey caKey, Date thisUpdate, Date nextUpdate,
            List<Certificate> revokedCerts) throws Exception {

        org.bouncycastle.cert.X509v2CRLBuilder crlBuilder =
                new org.bouncycastle.cert.X509v2CRLBuilder(issuer, thisUpdate);

        crlBuilder.setNextUpdate(nextUpdate);

        for (Certificate revoked : revokedCerts) {
            crlBuilder.addCRLEntry(
                    new BigInteger(revoked.getSerialNumber()),
                    revoked.getRevokedAt() != null
                            ? Date.from(revoked.getRevokedAt().toInstant())
                            : thisUpdate,
                    CRLReason.unspecified);
        }

        ContentSigner signer = new JcaContentSignerBuilder(caProperties.getSignatureAlgorithm())
                .setProvider(BouncyCastleProvider.PROVIDER_NAME)
                .build(caKey);

        return crlBuilder.build(signer);
    }
}
