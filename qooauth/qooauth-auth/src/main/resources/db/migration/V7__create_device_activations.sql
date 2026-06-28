-- ============================================================================
-- V7: Device Activation — first-boot activation, challenge-response, device-to-user binding
-- ============================================================================

-- 1. Device activations table
CREATE TABLE IF NOT EXISTS device_activations (
    activation_id       VARCHAR(64)     NOT NULL PRIMARY KEY,
    user_id             VARCHAR(32)     NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    device_id           VARCHAR(64)     NOT NULL,           -- References the robot/device (physical)
    cert_id             VARCHAR(64)     REFERENCES device_certificates(cert_id) ON DELETE SET NULL,
    device_serial       VARCHAR(128)    NOT NULL,           -- Manufacturer serial / hardware ID
    device_model        VARCHAR(128),                       -- e.g. "QooBot-Explorer", "QooBot-Companion"
    firmware_version    VARCHAR(32),
    hardware_fingerprint VARCHAR(256),                      -- Composite hardware fingerprint
    activation_state    VARCHAR(16)     NOT NULL DEFAULT 'PENDING', -- PENDING, CHALLENGED, ACTIVATED, FAILED, REVOKED
    bootstrap_cert_id   VARCHAR(64),                        -- Bootstrap certificate used during activation
    activation_token    VARCHAR(256),                       -- Encrypted activation token (AES-256-GCM)
    challenge_nonce     VARCHAR(128),                       -- Current challenge nonce
    challenge_issued_at TIMESTAMPTZ,
    challenge_expires_at TIMESTAMPTZ,
    challenge_attempts  INT             NOT NULL DEFAULT 0,
    max_challenge_attempts INT          NOT NULL DEFAULT 5,
    activated_at        TIMESTAMPTZ,
    expires_at          TIMESTAMPTZ,                        -- Activation session expiry (bootstrap window)
    failure_reason      VARCHAR(512),
    metadata            JSONB           DEFAULT '{}'::jsonb, -- IP, location, network info, activation context
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_device_activations_user_id ON device_activations(user_id);
CREATE INDEX IF NOT EXISTS idx_device_activations_device_id ON device_activations(device_id);
CREATE INDEX IF NOT EXISTS idx_device_activations_serial ON device_activations(device_serial);
CREATE INDEX IF NOT EXISTS idx_device_activations_state ON device_activations(activation_state);
CREATE INDEX IF NOT EXISTS idx_device_activations_token ON device_activations(activation_token);
CREATE INDEX IF NOT EXISTS idx_device_activations_expires ON device_activations(expires_at);

COMMENT ON TABLE device_activations IS 'Device first-boot activation sessions. Binds a physical robot to a QooBot ID account.';
COMMENT ON COLUMN device_activations.device_serial IS 'Manufacturer-assigned serial number engraved on the device';
COMMENT ON COLUMN device_activations.activation_token IS 'AES-256-GCM encrypted activation token, decryptable only by the device';
COMMENT ON COLUMN device_activations.challenge_nonce IS 'Cryptographic challenge nonce for device possession proof';

-- 2. Activation challenges (cryptographic attestation records)
CREATE TABLE IF NOT EXISTS activation_challenges (
    challenge_id        VARCHAR(64)     NOT NULL PRIMARY KEY,
    activation_id       VARCHAR(64)     NOT NULL REFERENCES device_activations(activation_id) ON DELETE CASCADE,
    device_id           VARCHAR(64)     NOT NULL,
    challenge_type      VARCHAR(32)     NOT NULL DEFAULT 'SIGNATURE', -- SIGNATURE, TPM_ATTESTATION, MAC, CUSTOM
    challenge_nonce     VARCHAR(128)    NOT NULL,
    expected_response_hash VARCHAR(64),                              -- SHA-256 of expected response
    actual_response     TEXT,                                        -- Device's response (signature, attestation, etc.)
    response_valid      BOOLEAN,
    challenge_state     VARCHAR(16)     NOT NULL DEFAULT 'PENDING',  -- PENDING, ACCEPTED, REJECTED, EXPIRED
    issued_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    responded_at        TIMESTAMPTZ,
    expires_at          TIMESTAMPTZ     NOT NULL,
    metadata            JSONB           DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_activation_challenges_activation ON activation_challenges(activation_id);
CREATE INDEX IF NOT EXISTS idx_activation_challenges_device ON activation_challenges(device_id);
CREATE INDEX IF NOT EXISTS idx_activation_challenges_state ON activation_challenges(challenge_state);
CREATE INDEX IF NOT EXISTS idx_activation_challenges_expires ON activation_challenges(expires_at);

COMMENT ON TABLE activation_challenges IS 'Cryptographic challenge-response records for device activation possession proof';
COMMENT ON COLUMN activation_challenges.challenge_type IS 'SIGNATURE: device signs nonce with bootstrap key; TPM_ATTESTATION: TPM quote; MAC: HMAC-based';
COMMENT ON COLUMN activation_challenges.expected_response_hash IS 'SHA-256 hash of the expected response for server-side verification';
