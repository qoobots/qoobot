-- ==============================================
-- qoocloud-inference — 推理服务 数据库初始化
-- ==============================================

CREATE TABLE IF NOT EXISTS inference_models (
    id              BIGSERIAL PRIMARY KEY,
    model_id        VARCHAR(128) NOT NULL UNIQUE,
    model_name      VARCHAR(256) NOT NULL,
    model_type      VARCHAR(64) NOT NULL,        -- VISION, LANGUAGE, MULTI_MODAL, VLA
    version         VARCHAR(32) NOT NULL,
    framework       VARCHAR(64),                  -- triton, vllm, ollama
    storage_path    VARCHAR(512),                 -- MinIO object path
    status          VARCHAR(32) NOT NULL DEFAULT 'OFFLINE',  -- ONLINE, OFFLINE, LOADING, ERROR
    config_json     TEXT,                         -- GPU/显存/批处理等配置 (JSON)
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inference_requests (
    id              BIGSERIAL PRIMARY KEY,
    request_id      VARCHAR(64) NOT NULL UNIQUE,
    model_id        VARCHAR(128) NOT NULL REFERENCES inference_models(model_id),
    device_id       VARCHAR(128),
    prompt_tokens   INTEGER,
    completion_tokens INTEGER,
    latency_ms      INTEGER,
    status          VARCHAR(32) NOT NULL,         -- SUCCESS, ERROR, TIMEOUT
    error_message   TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_inference_models_type    ON inference_models(model_type);
CREATE INDEX idx_inference_models_status  ON inference_models(status);
CREATE INDEX idx_inference_requests_model ON inference_requests(model_id);
CREATE INDEX idx_inference_requests_time  ON inference_requests(created_at);
