-- ==============================================
-- qoocloud-ota — OTA 升级 数据库初始化
-- ==============================================

CREATE TABLE IF NOT EXISTS ota_packages (
    id              BIGSERIAL PRIMARY KEY,
    package_id      VARCHAR(128) NOT NULL UNIQUE,
    package_name    VARCHAR(256) NOT NULL,
    package_type    VARCHAR(32) NOT NULL,     -- FIRMWARE, MODEL, SKILL, CONFIG
    version         VARCHAR(32) NOT NULL,
    target_models   TEXT[],                   -- 适用设备型号
    file_path       VARCHAR(512) NOT NULL,     -- MinIO 存储路径
    file_size       BIGINT,                   -- 字节
    file_hash       VARCHAR(128),             -- SHA-256
    release_notes   TEXT,
    status          VARCHAR(32) NOT NULL DEFAULT 'DRAFT',  -- DRAFT, PUBLISHED, DEPRECATED
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ota_tasks (
    id              BIGSERIAL PRIMARY KEY,
    task_id         VARCHAR(128) NOT NULL UNIQUE,
    package_id      VARCHAR(128) NOT NULL REFERENCES ota_packages(package_id),
    task_name       VARCHAR(256),
    strategy        VARCHAR(32) NOT NULL DEFAULT 'IMMEDIATE',  -- IMMEDIATE, SCHEDULED, IDLE, MANUAL
    canary_percent  INTEGER DEFAULT 10,        -- 灰度比例
    target_devices  TEXT[],                    -- 目标设备ID列表
    success_count   INTEGER DEFAULT 0,
    failure_count   INTEGER DEFAULT 0,
    total_count     INTEGER DEFAULT 0,
    status          VARCHAR(32) NOT NULL DEFAULT 'CREATED',  -- CREATED, CANARY, ROLLING, COMPLETED, FAILED, ROLLED_BACK
    scheduled_at    TIMESTAMP,
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    error_message   TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ota_task_logs (
    id              BIGSERIAL PRIMARY KEY,
    task_id         VARCHAR(128) NOT NULL REFERENCES ota_tasks(task_id),
    device_id       VARCHAR(128) NOT NULL,
    package_id      VARCHAR(128) NOT NULL,
    status          VARCHAR(32) NOT NULL,     -- DOWNLOADING, INSTALLING, SUCCESS, FAILED, ROLLED_BACK
    progress        INTEGER DEFAULT 0,        -- 0-100
    download_speed  DOUBLE PRECISION,         -- KB/s
    error_message   TEXT,
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_ota_packages_type   ON ota_packages(package_type);
CREATE INDEX idx_ota_packages_status ON ota_packages(status);
CREATE INDEX idx_ota_tasks_status    ON ota_tasks(status);
CREATE INDEX idx_ota_tasks_package   ON ota_tasks(package_id);
CREATE INDEX idx_ota_task_logs_task  ON ota_task_logs(task_id);
CREATE INDEX idx_ota_task_logs_device ON ota_task_logs(device_id);
