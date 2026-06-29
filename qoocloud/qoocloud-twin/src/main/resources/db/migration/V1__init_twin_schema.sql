-- ==============================================
-- qoocloud-twin — 数字孪生 数据库初始化
-- ==============================================

CREATE TABLE IF NOT EXISTS twin_environments (
    id              BIGSERIAL PRIMARY KEY,
    environment_id  VARCHAR(128) NOT NULL UNIQUE,
    device_id       VARCHAR(128) NOT NULL,
    environment_name VARCHAR(256),
    state_json      TEXT NOT NULL,            -- 环境完整状态 (JSON: 3D mesh, objects, lighting)
    objects_json    TEXT,                     -- 动态物体列表
    mesh_path       VARCHAR(512),            -- 3D 网格文件路径 (MinIO)
    version         INTEGER DEFAULT 1,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS twin_simulations (
    id              BIGSERIAL PRIMARY KEY,
    simulation_id   VARCHAR(128) NOT NULL UNIQUE,
    environment_id  VARCHAR(128) NOT NULL REFERENCES twin_environments(environment_id),
    simulation_name VARCHAR(256),
    task_json       TEXT NOT NULL,            -- 预演任务定义
    result_json     TEXT,                     -- 预演结果
    risk_score      DOUBLE PRECISION,        -- 风险评分 0-1
    duration_ms     BIGINT,
    status          VARCHAR(32) NOT NULL DEFAULT 'PENDING',  -- PENDING, RUNNING, COMPLETED, FAILED
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS twin_scene_library (
    id              BIGSERIAL PRIMARY KEY,
    scene_id        VARCHAR(128) NOT NULL UNIQUE,
    scene_name      VARCHAR(256) NOT NULL,
    scene_type      VARCHAR(64) NOT NULL,     -- HOME, WAREHOUSE, HOSPITAL, FACTORY, OFFICE
    description     TEXT,
    template_json   TEXT NOT NULL,            -- 场景模板 (3D layout, object set)
    thumbnail_path  VARCHAR(512),
    tags            TEXT[],
    status          VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS twin_replays (
    id              BIGSERIAL PRIMARY KEY,
    replay_id       VARCHAR(128) NOT NULL UNIQUE,
    device_id       VARCHAR(128) NOT NULL,
    task_id         VARCHAR(128),
    replay_name     VARCHAR(256),
    trace_json      TEXT NOT NULL,            -- 轨迹回放数据
    duration_ms     BIGINT,
    root_cause      VARCHAR(64),             -- COLLISION, SENSOR_FAILURE, PLANNING_ERROR, COMMUNICATION
    analysis_json   TEXT,                     -- 根因分析结果
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_twin_env_device    ON twin_environments(device_id);
CREATE INDEX idx_twin_sim_env       ON twin_simulations(environment_id);
CREATE INDEX idx_twin_sim_status    ON twin_simulations(status);
CREATE INDEX idx_twin_scene_type    ON twin_scene_library(scene_type);
CREATE INDEX idx_twin_scene_tags    ON twin_scene_library USING GIN(tags);
CREATE INDEX idx_twin_replay_device ON twin_replays(device_id);
