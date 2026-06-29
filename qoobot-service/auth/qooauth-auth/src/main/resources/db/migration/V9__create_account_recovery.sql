-- V9: Account Recovery Tables
-- Supports: recovery keys, backup email, trusted device recovery

-- Recovery codes (one-time use, user-generated)
CREATE TABLE IF NOT EXISTS recovery_codes (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         VARCHAR(32)     NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    code_hash       VARCHAR(255)    NOT NULL,       -- SHA-256 hash of recovery code
    label           VARCHAR(128),                   -- user-defined label (e.g. "Recovery Code 1")
    used            BOOLEAN         NOT NULL DEFAULT FALSE,
    used_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ                     -- NULL = never expires
);

CREATE INDEX idx_recovery_codes_user_id ON recovery_codes(user_id);
CREATE INDEX idx_recovery_codes_user_used ON recovery_codes(user_id, used);

-- Backup email addresses for account recovery
CREATE TABLE IF NOT EXISTS backup_emails (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         VARCHAR(32)     NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    email           VARCHAR(255)    NOT NULL,
    verified        BOOLEAN         NOT NULL DEFAULT FALSE,
    verification_token_hash VARCHAR(255),
    verified_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_backup_emails_user_email ON backup_emails(user_id, email);
CREATE INDEX idx_backup_emails_user_verified ON backup_emails(user_id, verified);

-- Recovery sessions (track in-progress recovery flows)
CREATE TABLE IF NOT EXISTS recovery_sessions (
    id              BIGSERIAL       PRIMARY KEY,
    session_token   VARCHAR(128)    NOT NULL UNIQUE, -- short-lived recovery token
    user_id         VARCHAR(32)     NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    method          VARCHAR(32)     NOT NULL,         -- RECOVERY_CODE / BACKUP_EMAIL / TRUSTED_DEVICE
    state           VARCHAR(32)     NOT NULL DEFAULT 'INITIATED',
    -- INITIATED / CODE_VERIFIED / EMAIL_VERIFIED / DEVICE_VERIFIED / COMPLETED / EXPIRED / FAILED
    attempts        INT             NOT NULL DEFAULT 0,
    max_attempts    INT             NOT NULL DEFAULT 5,
    ip_address      VARCHAR(45),
    user_agent      TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ     NOT NULL,         -- typically 15 minutes
    completed_at    TIMESTAMPTZ
);

CREATE INDEX idx_recovery_sessions_user ON recovery_sessions(user_id);
CREATE INDEX idx_recovery_sessions_token ON recovery_sessions(session_token);
CREATE INDEX idx_recovery_sessions_state ON recovery_sessions(user_id, state);
