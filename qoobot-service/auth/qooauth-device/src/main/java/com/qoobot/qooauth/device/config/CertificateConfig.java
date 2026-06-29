package com.qoobot.qooauth.device.config;

import org.bouncycastle.jce.provider.BouncyCastleProvider;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.security.Security;
import java.time.Period;

/**
 * Certificate Authority configuration for X.509 ECDSA P-256 device certificates.
 * <p>
 * Registers BouncyCastle as a security provider and exposes CA configuration
 * properties (key store location, certificate validity, etc.) from application.yml.
 */
@Configuration
public class CertificateConfig {

    private static final Logger log = LoggerFactory.getLogger(CertificateConfig.class);

    static {
        // Ensure BouncyCastle is registered before any crypto operations
        if (Security.getProvider(BouncyCastleProvider.PROVIDER_NAME) == null) {
            Security.addProvider(new BouncyCastleProvider());
            log.info("Registered BouncyCastle security provider");
        }
    }

    @Bean
    @ConfigurationProperties(prefix = "qooauth.device.ca")
    public CaProperties caProperties() {
        return new CaProperties();
    }

    /**
     * Holds CA configuration values loaded from application.yml.
     */
    public static class CaProperties {

        /** Path to the CA private key in PKCS#8 PEM format (or HSM alias). */
        private String keyPath = "/etc/qooauth/ca/device-ca-key.pem";

        /** Path to the CA certificate in PEM format. */
        private String certPath = "/etc/qooauth/ca/device-ca-cert.pem";

        /** HSM provider name if using HSM-backed keys (e.g. "SunPKCS11-nCipher"). */
        private String hsmProvider;

        /** HSM key alias when the CA key resides in an HSM. */
        private String hsmKeyAlias;

        /** Validity period for issued device certificates. */
        private Period certValidity = Period.ofYears(5);

        /** Validity period for renewal / re-issued certificates. */
        private Period renewalValidity = Period.ofYears(1);

        /** Signature algorithm for ECDSA P-256. */
        private String signatureAlgorithm = "SHA256withECDSA";

        /** EC curve name. */
        private String ecCurve = "secp256r1";

        /** Distinguished-name pattern: CN=dev-{serial}, O=QooBot, OU=Device */
        private String subjectDnPattern = "CN={serial},OU=Device,O=QooBot";

        // --- Getters / Setters ---

        public String getKeyPath() { return keyPath; }
        public void setKeyPath(String keyPath) { this.keyPath = keyPath; }
        public String getCertPath() { return certPath; }
        public void setCertPath(String certPath) { this.certPath = certPath; }
        public String getHsmProvider() { return hsmProvider; }
        public void setHsmProvider(String hsmProvider) { this.hsmProvider = hsmProvider; }
        public String getHsmKeyAlias() { return hsmKeyAlias; }
        public void setHsmKeyAlias(String hsmKeyAlias) { this.hsmKeyAlias = hsmKeyAlias; }
        public Period getCertValidity() { return certValidity; }
        public void setCertValidity(Period certValidity) { this.certValidity = certValidity; }
        public Period getRenewalValidity() { return renewalValidity; }
        public void setRenewalValidity(Period renewalValidity) { this.renewalValidity = renewalValidity; }
        public String getSignatureAlgorithm() { return signatureAlgorithm; }
        public void setSignatureAlgorithm(String signatureAlgorithm) { this.signatureAlgorithm = signatureAlgorithm; }
        public String getEcCurve() { return ecCurve; }
        public void setEcCurve(String ecCurve) { this.ecCurve = ecCurve; }
        public String getSubjectDnPattern() { return subjectDnPattern; }
        public void setSubjectDnPattern(String subjectDnPattern) { this.subjectDnPattern = subjectDnPattern; }
    }
}
