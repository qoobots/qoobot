-- 003: 设备表
-- 管理机器人设备身份，每台机器人拥有唯一 X.509 证书

CREATE TABLE devices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_name     VARCHAR(100) NOT NULL,
    device_type     VARCHAR(32) NOT NULL
                    CHECK (device_type IN ('home_robot', 'factory_robot', 'accessory')),
    serial_number   VARCHAR(64) NOT NULL UNIQUE,
    certificate_fp  VARCHAR(128) NOT NULL,    -- X.509 SHA-256 指纹
    public_key_pem  TEXT NOT NULL,            -- 设备公钥 PEM
    firmware_version VARCHAR(32),
    hardware_model  VARCHAR(64),
    online_status   VARCHAR(16) NOT NULL DEFAULT 'offline'
                    CHECK (online_status IN ('online', 'offline', 'busy')),
    last_seen_at    TIMESTAMPTZ,
    last_location   JSONB,                    -- {lat, lng, address}
    activation_locked BOOLEAN NOT NULL DEFAULT FALSE,
    lock_reason     VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_devices_user ON devices(user_id);
CREATE INDEX idx_devices_cert ON devices(certificate_fp);
CREATE UNIQUE INDEX idx_devices_serial ON devices(serial_number);

CREATE TRIGGER trg_devices_updated_at
    BEFORE UPDATE ON devices
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
