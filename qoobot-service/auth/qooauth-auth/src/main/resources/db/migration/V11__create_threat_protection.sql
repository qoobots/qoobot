-- ============================================================================
-- V11: Threat Protection — anomaly events, device fingerprints, IP reputation
-- ============================================================================

-- 1. Anomaly Events table (login anomaly detection)
CREATE TABLE IF NOT EXISTS anomaly_events (
    event_id            VARCHAR(64)     NOT NULL PRIMARY KEY,
    user_id             VARCHAR(32)     REFERENCES users(user_id) ON DELETE SET NULL,
    event_type          VARCHAR(32)     NOT NULL,       -- 'LOGIN_ANOMALY', 'DEVICE_ANOMALY', 'API_ANOMALY'
    risk_score          DOUBLE PRECISION NOT NULL,       -- 0.0 to 1.0
    risk_level          VARCHAR(16)     NOT NULL,       -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    ip_address          VARCHAR(45),
    geo_country         VARCHAR(8),
    geo_city            VARCHAR(128),
    device_fingerprint  VARCHAR(256),
    user_agent          VARCHAR(512),
    anomaly_reasons     JSONB           DEFAULT '[]'::jsonb,
    features            JSONB           DEFAULT '{}'::jsonb,
    action_taken        VARCHAR(32),                    -- 'ALLOW', 'FLAG_REVIEW', 'CHALLENGE_MFA', 'BLOCK'
    is_resolved         BOOLEAN         NOT NULL DEFAULT FALSE,
    resolved_by         VARCHAR(32),
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anomaly_events_user_id ON anomaly_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_events_ip ON anomaly_events(ip_address, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_events_risk_level ON anomaly_events(risk_level, is_resolved);
CREATE INDEX IF NOT EXISTS idx_anomaly_events_type ON anomaly_events(event_type, created_at DESC);

COMMENT ON TABLE anomaly_events IS 'Anomaly detection events for login and API behavior analysis';
COMMENT ON COLUMN anomaly_events.risk_score IS 'Aggregated risk score from multi-dimensional feature analysis (0.0–1.0)';
COMMENT ON COLUMN anomaly_events.anomaly_reasons IS 'JSON array of anomaly reason codes (e.g., GEO_NEW_COUNTRY, DEVICE_ANOMALY)';
COMMENT ON COLUMN anomaly_events.features IS 'JSON map of feature name → score for ML model training';

-- 2. Device Fingerprints table (browser/device identity tracking)
CREATE TABLE IF NOT EXISTS device_fingerprints (
    fingerprint_id     VARCHAR(64)     NOT NULL PRIMARY KEY,
    user_id            VARCHAR(32)     NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    fingerprint_hash   VARCHAR(256)    NOT NULL,
    device_type        VARCHAR(32),                    -- 'browser', 'mobile_app', 'desktop', 'robot'
    browser_name       VARCHAR(64),
    browser_version    VARCHAR(32),
    os_name            VARCHAR(64),
    os_version         VARCHAR(32),
    screen_resolution  VARCHAR(16),
    timezone_offset    INTEGER,
    language           VARCHAR(10),
    canvas_hash        VARCHAR(64),
    webgl_hash         VARCHAR(64),
    font_hash          VARCHAR(64),
    first_seen_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    last_seen_at       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    use_count          INTEGER         NOT NULL DEFAULT 1,
    risk_score         DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_device_fp_user_hash ON device_fingerprints(user_id, fingerprint_hash);
CREATE INDEX IF NOT EXISTS idx_device_fp_risk ON device_fingerprints(risk_score DESC);

COMMENT ON TABLE device_fingerprints IS 'Device identity tracking using browser canvas/WebGL/font fingerprinting';
COMMENT ON COLUMN device_fingerprints.canvas_hash IS 'SHA-256 hash of browser canvas rendering fingerprint';
COMMENT ON COLUMN device_fingerprints.webgl_hash IS 'SHA-256 hash of WebGL renderer fingerprint';
COMMENT ON COLUMN device_fingerprints.font_hash IS 'SHA-256 hash of installed fonts list';

-- 3. IP Reputation table (IP address trust scoring)
CREATE TABLE IF NOT EXISTS ip_reputation (
    reputation_id      VARCHAR(64)     NOT NULL PRIMARY KEY,
    ip_address         VARCHAR(45)     NOT NULL,
    ip_version         VARCHAR(4)      NOT NULL DEFAULT 'v4',
    total_attempts     BIGINT          NOT NULL DEFAULT 0,
    failure_count      BIGINT          NOT NULL DEFAULT 0,
    success_count      BIGINT          NOT NULL DEFAULT 0,
    last_seen_at       TIMESTAMPTZ,
    first_seen_at      TIMESTAMPTZ,
    is_blocked         BOOLEAN         NOT NULL DEFAULT FALSE,
    blocked_at         TIMESTAMPTZ,
    blocked_reason     VARCHAR(256),
    risk_score         DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    geo_country        VARCHAR(8),
    geo_city           VARCHAR(128),
    isp_name           VARCHAR(128),
    is_datacenter      BOOLEAN         NOT NULL DEFAULT FALSE,
    is_tor_exit        BOOLEAN         NOT NULL DEFAULT FALSE,
    is_vpn             BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ip_reputation_address ON ip_reputation(ip_address);
CREATE INDEX IF NOT EXISTS idx_ip_reputation_blocked ON ip_reputation(is_blocked, risk_score DESC);

COMMENT ON TABLE ip_reputation IS 'IP address reputation tracking for brute-force and credential stuffing detection';
COMMENT ON COLUMN ip_reputation.is_datacenter IS 'Whether IP belongs to a cloud/hosting provider (higher risk)';
COMMENT ON COLUMN ip_reputation.is_tor_exit IS 'Whether IP is a known Tor exit node';
COMMENT ON COLUMN ip_reputation.is_vpn IS 'Whether IP is a known VPN/proxy service';
