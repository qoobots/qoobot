-- ==============================================
-- qoocloud-orchestra — 多机器人编排 数据库初始化
-- ==============================================

CREATE TABLE IF NOT EXISTS robot_clusters (
    id              BIGSERIAL PRIMARY KEY,
    cluster_id      VARCHAR(128) NOT NULL UNIQUE,
    cluster_name    VARCHAR(256) NOT NULL,
    cluster_type    VARCHAR(64) NOT NULL DEFAULT 'STATIC',  -- STATIC, AD_HOC, TASK_BASED
    description     TEXT,
    member_ids      TEXT[],                   -- 成员设备ID列表
    leader_id       VARCHAR(128),
    topology_json   TEXT,                     -- 拓扑结构 (JSON)
    status          VARCHAR(32) NOT NULL DEFAULT 'INACTIVE',  -- ACTIVE, INACTIVE, DISBANDED
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orchestration_tasks (
    id              BIGSERIAL PRIMARY KEY,
    task_id         VARCHAR(128) NOT NULL UNIQUE,
    task_name       VARCHAR(256) NOT NULL,
    task_type       VARCHAR(64) NOT NULL,     -- COLLABORATIVE_TRANSPORT, AREA_COVERAGE, SORTING, SEARCH
    priority        INTEGER DEFAULT 5,        -- 1-10, 10最高
    required_devices INTEGER DEFAULT 1,
    constraints_json TEXT,                    -- 约束条件 (位置/能力/时间窗)
    assigned_devices TEXT[],                  -- 分配的设备ID列表
    schedule_json   TEXT,                     -- 调度计划
    status          VARCHAR(32) NOT NULL DEFAULT 'PENDING',  -- PENDING, ASSIGNED, EXECUTING, COMPLETED, FAILED
    progress        DOUBLE PRECISION DEFAULT 0, -- 0-100
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orchestration_scenes (
    id              BIGSERIAL PRIMARY KEY,
    scene_id        VARCHAR(128) NOT NULL UNIQUE,
    scene_name      VARCHAR(256) NOT NULL,
    scene_type      VARCHAR(64) NOT NULL,     -- WAREHOUSE, HOSPITAL, HOME, FACTORY
    description     TEXT,
    workflow_json   TEXT,                     -- 协作工作流定义 (JSON)
    robot_roles     TEXT,                     -- 角色分配定义 (JSON)
    status          VARCHAR(32) NOT NULL DEFAULT 'DRAFT',  -- DRAFT, PUBLISHED, ARCHIVED
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_clusters_status      ON robot_clusters(status);
CREATE INDEX idx_clusters_members     ON robot_clusters USING GIN(member_ids);
CREATE INDEX idx_tasks_status         ON orchestration_tasks(status);
CREATE INDEX idx_tasks_priority       ON orchestration_tasks(priority);
CREATE INDEX idx_tasks_assigned       ON orchestration_tasks USING GIN(assigned_devices);
CREATE INDEX idx_scenes_type          ON orchestration_scenes(scene_type);
