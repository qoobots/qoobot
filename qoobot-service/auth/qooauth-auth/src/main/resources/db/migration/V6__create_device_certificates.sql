-- ============================================================================
-- V6: X.509 Device Certificates — ECDSA P-256 issuance, renewal, revocation, CRL
-- ============================================================================

-- 1. Device certificates table
CREATE TABLE IF NOT EXISTS device_certificates (
    cert_id             VARCHAR(64)     NOT NULL PRIMARY KEY,
    user_id             VARCHAR(32)     REFERENCES users(user_id) ON DELETE SET NULL,
    device_id           VARCHAR(64)     NOT NULL,           -- References the robot/device
    serial_number       VARCHAR(40)     NOT NULL UNIQUE,    -- X.509 serial number (hex)
    subject_dn          VARCHAR(512)    NOT NULL,           -- X.509 Subject DN (e.g. CN=robot-001,O=QooBot)
    issuer_dn           VARCHAR(512)    NOT NULL,           -- CA issuer DN
    public_key_pem      TEXT            NOT NULL,           -- PEM-encoded ECDSA P-256 public key
    cert_pem            TEXT            NOT NULL,           -- PEM-encoded X.509 certificate
    fingerprint_sha256  VARCHAR(64)     NOT NULL UNIQUE,    -- SHA-256 fingerprint of DER cert
    key_algorithm       VARCHAR(16)     NOT NULL DEFAULT 'ECDSA_P256',
    not_before          TIMESTAMPTZ     NOT NULL,
    not_after           TIMESTAMPTZ     NOT NULL,
    state               VARCHAR(16)     NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, RENEWING, REVOKED, EXPIRED
    revocation_date     TIMESTAMPTZ,
    revocation_reason   VARCHAR(128),                       -- keyCompromise, affiliationChanged, superseded, cessationOfOperation, privilegeWithdrawn
    auto_renew          BOOLEAN         NOT NULL DEFAULT TRUE,
    renew_threshold_days INT            DEFAULT 30,          -- Renew this many days before expiry
    metadata            JSONB           DEFAULT '{}'::jsonb, -- device model, firmware version, hardware fingerprint
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_device_certs_user_id ON device_certificates(user_id);
CREATE INDEX IF NOT EXISTS idx_device_certs_device_id ON device_certificates(device_id);
CREATE INDEX IF NOT EXISTS idx_device_certs_serial ON device_certificates(serial_number);
CREATE INDEX IF NOT EXISTS idx_device_certs_fingerprint ON device_certificates(fingerprint_sha256);
CREATE INDEX IF NOT EXISTS idx_device_certs_state ON device_certificates(state);
CREATE INDEX IF NOT EXISTS idx_device_certs_not_after ON device_certificates(not_after);

COMMENT ON TABLE device_certificates IS 'X.509 device identity certificates issued by QooBot Device CA (ECDSA P-256)';
COMMENT ON COLUMN device_certificates.serial_number IS 'X.509 certificate serial number in hexadecimal';
COMMENT ON COLUMN device_certificates.fingerprint_sha256 IS 'SHA-256 hash of DER-encoded certificate for quick lookup';
COMMENT ON COLUMN device_certificates.metadata IS 'JSON: device model, firmware version, hardware fingerprint, TPM attestation';

-- 2. CRL (Certificate Revocation List) entries
CREATE TABLE IF NOT EXISTS crl_entries (
    entry_id            VARCHAR(64)     NOT NULL PRIMARY KEY,
    serial_number       VARCHAR(40)     NOT NULL,           -- Revoked certificate serial
    cert_id             VARCHAR(64)     REFERENCES device_certificates(cert_id) ON DELETE CASCADE,
    revocation_date     TIMESTAMPTZ     NOT NULL,
    revocation_reason   VARCHAR(128)    NOT NULL,           -- keyCompromise, affiliationChanged, superseded, cessationOfOperation, privilegeWithdrawn, removeFromCRL
    invalidity_date     TIMESTAMPTZ,                        -- When the compromise is suspected to have occurred
    crl_number          BIGINT          NOT NULL,           -- Monotonically increasing CRL sequence number
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crl_serial ON crl_entries(serial_number);
CREATE INDEX IF NOT EXISTS idx_crl_date ON crl_entries(revocation_date DESC);
CREATE INDEX IF NOT EXISTS idx_crl_number ON crl_entries(crl_number DESC);

COMMENT ON TABLE crl_entries IS 'Certificate Revocation List entries (RFC 5280 Section 5)';
COMMENT ON COLUMN crl_entries.invalidity_date IS 'RFC 5280: suspected time of private key compromise';
COMMENT ON COLUMN crl_entries.crl_number IS 'Monotonically increasing CRL number per RFC 5280 Section 5.2.3';

-- 3. Device CA configuration table
CREATE TABLE IF NOT EXISTS device_ca_config (
    ca_id               VARCHAR(64)     NOT NULL PRIMARY KEY,
    ca_name             VARCHAR(128)    NOT NULL,
    ca_cert_pem         TEXT            NOT NULL,           -- CA's own certificate (PEM)
    ca_private_key_enc  TEXT            NOT NULL,           -- CA private key (AES-256-GCM encrypted)
    key_algorithm       VARCHAR(16)     NOT NULL DEFAULT 'ECDSA_P256',
    serial_counter      BIGINT          NOT NULL DEFAULT 1, -- Monotonically increasing serial
    crl_number          BIGINT          NOT NULL DEFAULT 0, -- CRL sequence number
    default_validity_days INT           NOT NULL DEFAULT 365,
    max_validity_days   INT             NOT NULL DEFAULT 730,
    next_crl_update     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    crl_update_interval_hours INT       NOT NULL DEFAULT 24,
    state               VARCHAR(16)     NOT NULL DEFAULT 'ACTIVE',
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE device_ca_config IS 'Device Certificate Authority configuration and key material';
COMMENT ON COLUMN device_ca_config.ca_private_key_enc IS 'CA private key encrypted with AES-256-GCM using KMS-derived key';
