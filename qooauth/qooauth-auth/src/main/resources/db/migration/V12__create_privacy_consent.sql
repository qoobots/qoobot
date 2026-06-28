-- ============================================================================
-- V12: Privacy & Consent Management — consent records, retention policies, privacy labels
-- ============================================================================

-- 1. Consent Records table (GDPR/CCPA/PIPL compliance)
CREATE TABLE IF NOT EXISTS consent_records (
    consent_id              VARCHAR(64)     NOT NULL PRIMARY KEY,
    user_id                 VARCHAR(32)     NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    purpose                 VARCHAR(64)     NOT NULL,       -- 'analytics', 'personalization', 'location', etc.
    granted                 BOOLEAN         NOT NULL,
    ip_address              VARCHAR(45),
    user_agent              VARCHAR(512),
    consent_version         VARCHAR(16),                    -- version of consent form
    privacy_policy_version  VARCHAR(16),                    -- version of privacy policy at time of consent
    granted_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    expires_at              TIMESTAMPTZ,                    -- consent expiry (null = until revoked)
    revoked_at              TIMESTAMPTZ                     -- when consent was withdrawn
);

CREATE INDEX IF NOT EXISTS idx_consent_user_id ON consent_records(user_id, purpose);
CREATE INDEX IF NOT EXISTS idx_consent_active ON consent_records(user_id, granted, revoked_at, expires_at);
CREATE INDEX IF NOT EXISTS idx_consent_expired ON consent_records(expires_at) WHERE revoked_at IS NULL;

COMMENT ON TABLE consent_records IS 'User consent records for data processing purposes (GDPR Art. 7)';
COMMENT ON COLUMN consent_records.purpose IS 'Processing purpose: analytics, personalization, location, advertising, diagnostics, third_party_sharing, marketing';

-- 2. Data Retention Policies table (data minimization)
CREATE TABLE IF NOT EXISTS data_retention_policies (
    policy_id       VARCHAR(64)     NOT NULL PRIMARY KEY,
    data_category   VARCHAR(64)     NOT NULL,               -- 'login_history', 'audit_logs', 'session_data', etc.
    retention_days  INTEGER         NOT NULL,
    auto_delete     BOOLEAN         NOT NULL DEFAULT TRUE,
    legal_basis     VARCHAR(128),                           -- 'Legitimate interest', 'Legal obligation', 'Consent'
    description     VARCHAR(512),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_retention_category ON data_retention_policies(data_category);

COMMENT ON TABLE data_retention_policies IS 'Data retention policies for data minimization compliance (GDPR Art. 5(1)(e))';
COMMENT ON COLUMN data_retention_policies.retention_days IS 'Maximum number of days data is retained before automatic deletion';

-- 3. Insert default retention policies
INSERT INTO data_retention_policies (policy_id, data_category, retention_days, auto_delete, legal_basis, description, created_at, updated_at)
VALUES
    ('ret_login_history', 'login_history', 90, TRUE, 'Legitimate interest - security', 'Login attempt records for security monitoring', NOW(), NOW()),
    ('ret_audit_logs', 'audit_logs', 365, TRUE, 'Legal obligation - compliance', 'Audit logs for regulatory compliance', NOW(), NOW()),
    ('ret_session_data', 'session_data', 30, TRUE, 'Legitimate interest - service operation', 'Active session and token data', NOW(), NOW()),
    ('ret_consent_records', 'consent_records', 730, FALSE, 'Legal obligation - consent proof', 'Consent records retained as proof of consent', NOW(), NOW()),
    ('ret_device_fingerprints', 'device_fingerprints', 180, TRUE, 'Legitimate interest - security', 'Device fingerprint data for fraud detection', NOW(), NOW()),
    ('ret_anomaly_events', 'anomaly_events', 365, TRUE, 'Legitimate interest - security', 'Anomaly detection events for security monitoring', NOW(), NOW())
ON CONFLICT (data_category) DO NOTHING;
