-- V14: Developer Program Infrastructure
-- Developer certificates, skill signatures, sandbox environments, and permission reviews

CREATE TABLE IF NOT EXISTS developer_certificates (
    cert_id             VARCHAR(64)     PRIMARY KEY,
    user_id             VARCHAR(64)     NOT NULL,
    cert_type           VARCHAR(16)     NOT NULL,
    serial_number       VARCHAR(64)     NOT NULL UNIQUE,
    subject_dn          VARCHAR(256)    NOT NULL,
    public_key_pem      TEXT            NOT NULL,
    cert_pem            TEXT            NOT NULL,
    fingerprint_sha256  VARCHAR(128)    NOT NULL,
    key_algorithm       VARCHAR(16)     NOT NULL DEFAULT 'ECDSA_P256',
    not_before          TIMESTAMP       NOT NULL,
    not_after           TIMESTAMP       NOT NULL,
    state               VARCHAR(16)     NOT NULL DEFAULT 'ACTIVE',
    team_id             VARCHAR(64),
    capabilities        TEXT,
    revoked_at          TIMESTAMP,
    revoke_reason       VARCHAR(256),
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS skill_signatures (
    signature_id            VARCHAR(64)     PRIMARY KEY,
    skill_id                VARCHAR(128)    NOT NULL,
    skill_version           VARCHAR(32)     NOT NULL,
    package_hash            VARCHAR(128)    NOT NULL,
    signature               TEXT            NOT NULL,
    developer_cert_id       VARCHAR(64)     NOT NULL REFERENCES developer_certificates(cert_id),
    developer_user_id       VARCHAR(64)     NOT NULL,
    timestamp_signature     TEXT,
    timestamp_authority_url VARCHAR(256),
    state                   VARCHAR(16)     NOT NULL DEFAULT 'VALID',
    metadata                TEXT,
    signed_at               TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at              TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sandbox_environments (
    env_id              VARCHAR(64)     PRIMARY KEY,
    user_id             VARCHAR(64)     NOT NULL,
    name                VARCHAR(128)    NOT NULL,
    state               VARCHAR(16)     NOT NULL DEFAULT 'ACTIVE',
    resource_limits     TEXT            NOT NULL,
    resource_usage      TEXT,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at          TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS permission_reviews (
    review_id               VARCHAR(64)     PRIMARY KEY,
    skill_id                VARCHAR(128)    NOT NULL,
    skill_version           VARCHAR(32)     NOT NULL,
    developer_user_id       VARCHAR(64)     NOT NULL,
    requested_permissions   TEXT            NOT NULL,
    justification           TEXT,
    state                   VARCHAR(32)     NOT NULL DEFAULT 'PENDING',
    decision                TEXT,
    reviewer_id             VARCHAR(64),
    reviewer_notes          TEXT,
    compliance_checks       TEXT,
    submitted_at            TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at             TIMESTAMP,
    created_at              TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_dc_user ON developer_certificates(user_id);
CREATE INDEX idx_dc_serial ON developer_certificates(serial_number);
CREATE INDEX idx_dc_state ON developer_certificates(state);
CREATE INDEX idx_ss_skill ON skill_signatures(skill_id);
CREATE INDEX idx_ss_cert ON skill_signatures(developer_cert_id);
CREATE INDEX idx_ss_state ON skill_signatures(state);
CREATE INDEX idx_se_user ON sandbox_environments(user_id);
CREATE INDEX idx_se_state ON sandbox_environments(state);
CREATE INDEX idx_pr_skill ON permission_reviews(skill_id);
CREATE INDEX idx_pr_state ON permission_reviews(state);
CREATE INDEX idx_pr_reviewer ON permission_reviews(reviewer_id);
