-- V3: 示教记录表
CREATE TABLE IF NOT EXISTS teaching_records (
    record_id       VARCHAR(36) PRIMARY KEY,
    session_id      VARCHAR(36) NOT NULL,
    operator_id     VARCHAR(128) NOT NULL,
    robot_id        VARCHAR(64) NOT NULL,

    name            VARCHAR(256) NOT NULL,
    description     TEXT,
    tags            JSONB DEFAULT '[]',

    duration_ms     BIGINT,
    frame_count     INTEGER,
    data_format     VARCHAR(32) DEFAULT 'v1.0',

    trajectory_path     VARCHAR(512),
    sensor_data_path    VARCHAR(512),
    video_path          VARCHAR(512),

    quality_score   REAL,
    is_verified     BOOLEAN DEFAULT FALSE,

    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_teaching_robot ON teaching_records(robot_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_teaching_operator ON teaching_records(operator_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_teaching_session ON teaching_records(session_id);
