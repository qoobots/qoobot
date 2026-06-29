-- ==============================================
-- qoocloud-data — 数据同步 数据库初始化
-- ==============================================

CREATE TABLE IF NOT EXISTS experience_data (
    id              BIGSERIAL PRIMARY KEY,
    experience_id   VARCHAR(128) NOT NULL UNIQUE,
    device_id       VARCHAR(128) NOT NULL,
    data_type       VARCHAR(64) NOT NULL,     -- IMAGE, POINT_CLOUD, TRAJECTORY, STATE, VIDEO
    storage_path    VARCHAR(512) NOT NULL,    -- MinIO 存储路径
    metadata_json   TEXT,                     -- 采集时间/位置/传感器参数等
    semantic_tags   TEXT[],                   -- 语义标签
    status          VARCHAR(32) NOT NULL DEFAULT 'RAW',  -- RAW, DEDUPED, CLEANED, ANNOTATED, ARCHIVED
    privacy_filtered BOOLEAN DEFAULT FALSE,
    file_size       BIGINT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_entries (
    id              BIGSERIAL PRIMARY KEY,
    knowledge_id    VARCHAR(128) NOT NULL UNIQUE,
    category        VARCHAR(64) NOT NULL,     -- SEMANTIC_MAP, OBJECT_LIBRARY, SKILL, SAFETY_RULE
    title           VARCHAR(256) NOT NULL,
    content_json    TEXT NOT NULL,
    source_devices  TEXT[],                   -- 来源设备
    version         INTEGER DEFAULT 1,
    status          VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE, DEPRECATED, ARCHIVED
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS federated_models (
    id              BIGSERIAL PRIMARY KEY,
    model_id        VARCHAR(128) NOT NULL UNIQUE,
    model_name      VARCHAR(256) NOT NULL,
    global_round    INTEGER DEFAULT 0,
    participants    INTEGER DEFAULT 0,
    weights_path    VARCHAR(512),             -- MinIO 存储路径
    metrics_json    TEXT,                     -- 准确率/损失等指标
    status          VARCHAR(32) NOT NULL DEFAULT 'TRAINING',  -- TRAINING, AGGREGATING, DEPLOYED
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data_pipelines (
    id              BIGSERIAL PRIMARY KEY,
    pipeline_id     VARCHAR(128) NOT NULL UNIQUE,
    pipeline_name   VARCHAR(256) NOT NULL,
    source_type     VARCHAR(64) NOT NULL,     -- REALTIME, BATCH
    transform_rules TEXT NOT NULL,            -- ETL 规则 (JSON)
    target_storage  VARCHAR(32) NOT NULL DEFAULT 'POSTGRES',  -- POSTGRES, MINIO, CLICKHOUSE
    status          VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_experience_device    ON experience_data(device_id);
CREATE INDEX idx_experience_type     ON experience_data(data_type);
CREATE INDEX idx_experience_status   ON experience_data(status);
CREATE INDEX idx_knowledge_category  ON knowledge_entries(category);
CREATE INDEX idx_knowledge_status    ON knowledge_entries(status);
CREATE INDEX idx_federated_status    ON federated_models(status);
