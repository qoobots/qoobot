-- ==============================================
-- qoocloud-device — 设备管理 数据库初始化
-- ==============================================

CREATE TABLE IF NOT EXISTS devices (
    id              BIGSERIAL PRIMARY KEY,
    device_id       VARCHAR(128) NOT NULL UNIQUE,
    device_name     VARCHAR(256),
    device_model    VARCHAR(64),              -- QJ-STANDARD, QJ-PRO, QJ-LITE
    serial_number   VARCHAR(64) UNIQUE,
    firmware_version VARCHAR(32),
    cert_fingerprint VARCHAR(128),            -- 设备证书指纹
    status          VARCHAR(32) NOT NULL DEFAULT 'REGISTERED',  -- REGISTERED, ACTIVE, MAINTENANCE, DECOMMISSIONED
    last_heartbeat  TIMESTAMP,
    ip_address      VARCHAR(45),
    location        TEXT,                     -- JSON: {lat, lng, geo_hash}
    cpu_usage       DOUBLE PRECISION,
    memory_usage    DOUBLE PRECISION,
    disk_usage      DOUBLE PRECISION,
    battery_level   DOUBLE PRECISION,
    temperature     DOUBLE PRECISION,
    config_json     TEXT,                     -- 云端下发配置 (JSON)
    owner_id        VARCHAR(128),
    group_id        VARCHAR(128),
    tags            TEXT[],                   -- PostgreSQL 数组
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS device_groups (
    id              BIGSERIAL PRIMARY KEY,
    group_id        VARCHAR(128) NOT NULL UNIQUE,
    group_name      VARCHAR(256) NOT NULL,
    group_type      VARCHAR(32) NOT NULL DEFAULT 'STATIC',  -- STATIC, DYNAMIC
    filter_rule     TEXT,                     -- 动态分组筛选规则 (JSON)
    description     TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS device_commands (
    id              BIGSERIAL PRIMARY KEY,
    command_id      VARCHAR(64) NOT NULL UNIQUE,
    device_id       VARCHAR(128) NOT NULL REFERENCES devices(device_id),
    command_type    VARCHAR(64) NOT NULL,     -- DIAGNOSE, REBOOT, CONFIG_UPDATE, MAINTENANCE
    payload         TEXT,
    status          VARCHAR(32) NOT NULL DEFAULT 'PENDING',  -- PENDING, SENT, EXECUTED, FAILED
    result          TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    executed_at     TIMESTAMP
);

-- 索引
CREATE INDEX idx_devices_status        ON devices(status);
CREATE INDEX idx_devices_owner         ON devices(owner_id);
CREATE INDEX idx_devices_last_heartbeat ON devices(last_heartbeat);
CREATE INDEX idx_device_commands_device ON device_commands(device_id);
CREATE INDEX idx_device_commands_status ON device_commands(status);
