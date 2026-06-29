-- V3: MFA (Multi-Factor Authentication) tables
-- Adds TOTP secret column to users, creates fido2_credentials and recovery_codes tables

-- Add TOTP secret column to users table
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(64);

-- Add recovery codes hash column to users table (bcrypt hashed, 10 codes)
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS recovery_codes_hash JSONB;

-- FIDO2/WebAuthn credentials table
CREATE TABLE IF NOT EXISTS fido2_credentials (
    credential_id   VARCHAR(64) PRIMARY KEY,
    user_id         VARCHAR(32)  NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    credential_name VARCHAR(128) NOT NULL DEFAULT 'Security Key',
    public_key      TEXT         NOT NULL,
    sign_count      BIGINT       NOT NULL DEFAULT 0,
    transports      JSONB        DEFAULT '[]',
    aaguid          VARCHAR(36),
    attestation     TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_used_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_fido2_user_id ON fido2_credentials(user_id);

-- Recovery codes table (one-time use backup codes)
CREATE TABLE IF NOT EXISTS recovery_codes (
    id              BIGSERIAL PRIMARY KEY,
    user_id         VARCHAR(32) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    code_hash       VARCHAR(128) NOT NULL,
    used            BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_recovery_codes_user ON recovery_codes(user_id, used);
