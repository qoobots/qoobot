-- ============================================================================
-- V8: Audit Logs — partitioned audit event storage, compliance-ready
-- ============================================================================

-- 1. Audit logs table (partitioned by event_time, monthly)
CREATE TABLE IF NOT EXISTS audit_logs (
    id              BIGSERIAL,
    event_id        UUID NOT NULL,
    event_time      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Actor
    actor_type      VARCHAR(32) NOT NULL,           -- USER / DEVICE / SERVICE / ADMIN / SYSTEM
    actor_id        VARCHAR(32) NOT NULL,
    actor_name      VARCHAR(128),                   -- Human-readable actor identifier

    -- Action
    action          VARCHAR(64) NOT NULL,           -- LOGIN / REGISTER / TOKEN_ISSUE / TOKEN_REFRESH / TOKEN_REVOKE /
                                                    -- MFA_ENROLL / MFA_VERIFY / MFA_RECOVERY /
                                                    -- PASSWORD_CHANGE / ACCOUNT_UPDATE / ACCOUNT_DELETE /
                                                    -- OAUTH_AUTHORIZE / OAUTH_TOKEN / OAUTH_CLIENT_REGISTER /
                                                    -- API_KEY_CREATE / API_KEY_ROTATE / API_KEY_REVOKE /
                                                    -- DEVICE_ACTIVATE / DEVICE_CERT_ISSUE / DEVICE_CERT_REVOKE /
                                                    -- SESSION_CREATE / SESSION_DESTROY / SESSION_EXPIRE /
                                                    -- SSO_LOGIN / SSO_LOGOUT / SSO_PROPAGATE /
                                                    -- ADMIN_USER_FREEZE / ADMIN_USER_DELETE / ADMIN_CONFIG_UPDATE
    resource_type   VARCHAR(32),                    -- USER / DEVICE / OAUTH_CLIENT / API_KEY / SESSION / MFA / CERTIFICATE
    resource_id     VARCHAR(32),
    resource_name   VARCHAR(256),                   -- Human-readable resource identifier

    -- Result
    result          VARCHAR(16) NOT NULL,           -- SUCCESS / FAILURE / DENIED / ERROR
    error_code      VARCHAR(32),
    error_message   VARCHAR(512),

    -- Context
    client_ip       INET,
    user_agent      VARCHAR(512),
    geo_country     VARCHAR(2),                     -- ISO 3166-1 alpha-2
    geo_city        VARCHAR(128),
    geo_region      VARCHAR(128),

    -- Request metadata
    request_id      VARCHAR(64),
    session_id      VARCHAR(64),
    client_id       VARCHAR(64),                    -- OAuth2 client_id
    auth_method     VARCHAR(32),                    -- PASSWORD / TOTP / WEBAUTHN / RECOVERY_CODE / SSO / API_KEY

    -- Details (flexible JSONB for action-specific data)
    details         JSONB,

    -- Distributed tracing
    trace_id        VARCHAR(64),
    span_id         VARCHAR(32),

    -- Integrity
    integrity_hash  VARCHAR(128),                   -- SHA-256 of (event_id + event_time + actor_id + action + resource_id + result + client_ip)

    PRIMARY KEY (event_time, id)
) PARTITION BY RANGE (event_time);

-- 2. Create monthly partitions (current month + next 2 months)
CREATE TABLE IF NOT EXISTS audit_logs_2026_06 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE IF NOT EXISTS audit_logs_2026_07 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE IF NOT EXISTS audit_logs_2026_08 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');

-- 3. Indexes (created on parent table, propagated to partitions)
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor_type, actor_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type, resource_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_audit_result ON audit_logs(result, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_audit_client_ip ON audit_logs(client_ip, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_audit_trace ON audit_logs(trace_id);
CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_logs(session_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_audit_event_id ON audit_logs(event_id);

-- 4. Audit log integrity chain table (Merkle tree root per time bucket)
CREATE TABLE IF NOT EXISTS audit_integrity_chain (
    id              BIGSERIAL PRIMARY KEY,
    bucket_start    TIMESTAMPTZ NOT NULL,           -- Start of the time bucket (hourly)
    bucket_end      TIMESTAMPTZ NOT NULL,           -- End of the time bucket
    merkle_root     VARCHAR(128) NOT NULL,          -- SHA-256 Merkle tree root of all events in bucket
    event_count     INTEGER NOT NULL DEFAULT 0,
    prev_chain_hash VARCHAR(128),                   -- Chain to previous bucket (blockchain-like)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verified_at     TIMESTAMPTZ,
    verified_by     VARCHAR(64),

    CONSTRAINT uq_audit_integrity_bucket UNIQUE (bucket_start, bucket_end)
);

CREATE INDEX IF NOT EXISTS idx_audit_integrity_chain_time ON audit_integrity_chain(bucket_start DESC);

-- 5. Audit retention policy table
CREATE TABLE IF NOT EXISTS audit_retention_policies (
    id              SERIAL PRIMARY KEY,
    action_pattern  VARCHAR(64) NOT NULL,           -- e.g. 'LOGIN', 'TOKEN_%' (SQL LIKE pattern)
    retention_days  INTEGER NOT NULL DEFAULT 1095,  -- Default: 3 years
    archive_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    priority        INTEGER NOT NULL DEFAULT 0,     -- Higher = checked first
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Default retention policies
INSERT INTO audit_retention_policies (action_pattern, retention_days, archive_enabled, priority) VALUES
    ('LOGIN',             365,  TRUE, 10),
    ('TOKEN_%',           365,  TRUE, 10),
    ('MFA_%',             365,  TRUE, 10),
    ('PASSWORD_%',        365,  TRUE, 10),
    ('ACCOUNT_%',         1095, TRUE, 20),
    ('DEVICE_%',          1095, TRUE, 20),
    ('SESSION_%',         365,  TRUE, 5),
    ('OAUTH_%',           730,  TRUE, 10),
    ('API_KEY_%',         730,  TRUE, 10),
    ('SSO_%',             365,  TRUE, 10),
    ('ADMIN_%',           1825, TRUE, 30),
    ('CERT_%',            1095, TRUE, 20),
    ('%',                 1095, TRUE, 0)            -- Catch-all default: 3 years
ON CONFLICT DO NOTHING;
