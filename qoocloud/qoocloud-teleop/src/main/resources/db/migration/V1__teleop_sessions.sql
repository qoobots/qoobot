-- V1: 遥控会话表
CREATE TABLE IF NOT EXISTS teleop_sessions (
    session_id      VARCHAR(36) PRIMARY KEY,
    robot_id        VARCHAR(64) NOT NULL,
    operator_id     VARCHAR(128) NOT NULL,
    operator_name   VARCHAR(128),
    control_mode    VARCHAR(16) NOT NULL DEFAULT 'AUTO',
    session_status  VARCHAR(16) NOT NULL DEFAULT 'INITIATING',
    media_types     JSONB NOT NULL DEFAULT '[]',

    sdp_offer       TEXT,
    sdp_answer      TEXT,
    ice_candidates  JSONB,

    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    connected_at    TIMESTAMP,
    takeover_at     TIMESTAMP,
    handover_at     TIMESTAMP,
    closed_at       TIMESTAMP,
    last_heartbeat  TIMESTAMP,

    command_count       BIGINT DEFAULT 0,
    video_bytes_sent    BIGINT DEFAULT 0,
    audio_bytes_sent    BIGINT DEFAULT 0,
    max_latency_ms      INTEGER DEFAULT 0,
    avg_latency_ms      INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sessions_robot ON teleop_sessions(robot_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_operator ON teleop_sessions(operator_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON teleop_sessions(session_status);
