-- ============================================================================
-- V4: Account Security — password change tracking, trusted devices, login history
-- ============================================================================

-- 1. Add password security columns to users
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS password_history JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN users.password_changed_at IS 'Timestamp of last password change';
COMMENT ON COLUMN users.password_history IS 'Previous Argon2id password hashes for reuse prevention (up to 5)';

-- 2. Trusted devices table
CREATE TABLE IF NOT EXISTS trusted_devices (
    device_id       VARCHAR(64)     NOT NULL PRIMARY KEY,
    user_id         VARCHAR(32)     NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    device_name     VARCHAR(128),
    device_type     VARCHAR(32)     NOT NULL,       -- 'browser', 'mobile_app', 'desktop_app', 'robot'
    os_name         VARCHAR(64),
    os_version      VARCHAR(32),
    browser_name    VARCHAR(64),
    browser_version VARCHAR(32),
    device_model    VARCHAR(128),
    fingerprint     VARCHAR(256)    NOT NULL,       -- Hashed device fingerprint
    ip_address      VARCHAR(45),
    user_agent      VARCHAR(512),
    is_trusted      BOOLEAN         NOT NULL DEFAULT FALSE,
    last_used_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_trusted_devices_user_id ON trusted_devices(user_id);
CREATE INDEX IF NOT EXISTS idx_trusted_devices_fingerprint ON trusted_devices(user_id, fingerprint);

COMMENT ON TABLE trusted_devices IS 'User trusted/bound devices for 2FA bypass and session management';
COMMENT ON COLUMN trusted_devices.fingerprint IS 'SHA-256 hash of device fingerprint (browser canvas + WebGL + fonts)';

-- 3. Login history table
CREATE TABLE IF NOT EXISTS login_history (
    login_id        VARCHAR(64)     NOT NULL PRIMARY KEY,
    user_id         VARCHAR(32)     NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    success         BOOLEAN         NOT NULL,
    failure_reason  VARCHAR(128),                  -- 'INVALID_PASSWORD', 'ACCOUNT_LOCKED', 'MFA_FAILED', etc.
    ip_address      VARCHAR(45),
    user_agent      VARCHAR(512),
    device_fingerprint VARCHAR(256),
    device_name     VARCHAR(128),
    geo_country     VARCHAR(8),
    geo_city        VARCHAR(128),
    client_id       VARCHAR(64),
    mfa_used        BOOLEAN         NOT NULL DEFAULT FALSE,
    mfa_method      VARCHAR(16),                   -- 'totp', 'fido2', 'recovery'
    session_id      VARCHAR(64),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_login_history_user_id ON login_history(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_login_history_user_success ON login_history(user_id, success, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_login_history_ip ON login_history(ip_address, created_at DESC);

COMMENT ON TABLE login_history IS 'Audit trail of all login attempts (success and failure)';
COMMENT ON COLUMN login_history.geo_country IS 'ISO 3166-1 alpha-2 country code from GeoIP lookup';
