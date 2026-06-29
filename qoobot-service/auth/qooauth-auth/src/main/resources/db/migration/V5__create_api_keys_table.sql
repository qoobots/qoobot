-- ============================================================================
-- V5: API Key Management — key generation, rotation, revocation, permissions, quotas
-- ============================================================================

-- 1. API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    key_id          VARCHAR(64)     NOT NULL PRIMARY KEY,
    user_id         VARCHAR(32)     NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    key_name        VARCHAR(128)    NOT NULL,           -- User-friendly name (e.g. "My CLI Tool")
    key_prefix      VARCHAR(12)     NOT NULL,           -- First 8 chars of key for display (e.g. "qk_a1b2c3d4")
    key_hash        VARCHAR(255)    NOT NULL,           -- SHA-256 hash of the full API key
    key_type        VARCHAR(16)     NOT NULL DEFAULT 'API', -- 'API', 'ROBOT', 'DEVELOPER'
    state           VARCHAR(16)     NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'REVOKED', 'EXPIRED'
    scopes          JSONB           NOT NULL DEFAULT '["openid","profile","email"]'::jsonb,
    resource_ids    JSONB,                              -- Fine-grained resource access (e.g. ["devices/ro", "skills/rw"])
    rate_limit      INT             DEFAULT 1000,       -- Requests per hour
    quota_limit     INT             DEFAULT 10000,      -- Total requests per month
    quota_used      INT             NOT NULL DEFAULT 0,
    quota_reset_at  TIMESTAMPTZ     NOT NULL DEFAULT (DATE_TRUNC('month', NOW()) + INTERVAL '1 month'),
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    revoked_at      TIMESTAMPTZ,
    revoked_reason  VARCHAR(256)
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_state ON api_keys(state);

COMMENT ON TABLE api_keys IS 'User-managed API keys for programmatic access to QooBot services';
COMMENT ON COLUMN api_keys.key_prefix IS 'First 8 chars of the raw key for display (never store the full key in plaintext)';
COMMENT ON COLUMN api_keys.key_hash IS 'SHA-256 hash of the full API key for verification';
COMMENT ON COLUMN api_keys.scopes IS 'OAuth-style scope strings (openid, profile, email, skills:read, skills:write, etc.)';
COMMENT ON COLUMN api_keys.resource_ids IS 'Fine-grained resource paths with access level (e.g. ["devices/ro", "skills/rw"])';
COMMENT ON COLUMN api_keys.rate_limit IS 'Maximum requests per hour for this key';
COMMENT ON COLUMN api_keys.quota_limit IS 'Maximum total requests per calendar month';
COMMENT ON COLUMN api_keys.quota_reset_at IS 'Timestamp when the monthly quota counter resets';

-- 2. API Key usage log (for audit and quota tracking)
CREATE TABLE IF NOT EXISTS api_key_usage (
    usage_id        VARCHAR(64)     NOT NULL PRIMARY KEY,
    key_id          VARCHAR(64)     NOT NULL REFERENCES api_keys(key_id) ON DELETE CASCADE,
    endpoint        VARCHAR(256)    NOT NULL,           -- Requested API endpoint
    method          VARCHAR(8)      NOT NULL,           -- HTTP method
    status_code     INT             NOT NULL,           -- Response status
    duration_ms     INT,                                -- Request duration
    ip_address      VARCHAR(45),
    user_agent      VARCHAR(512),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_key_usage_key_id ON api_key_usage(key_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_key_usage_created_at ON api_key_usage(created_at DESC);

COMMENT ON TABLE api_key_usage IS 'Audit log of all API key usage for quota tracking and anomaly detection';

-- 3. Quota reset month column index
CREATE INDEX IF NOT EXISTS idx_api_keys_quota_reset ON api_keys(quota_reset_at);
