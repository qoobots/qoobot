-- V2: 控制指令记录表
CREATE TABLE IF NOT EXISTS control_commands (
    command_id      VARCHAR(36) PRIMARY KEY,
    session_id      VARCHAR(36) NOT NULL REFERENCES teleop_sessions(session_id),
    sequence        BIGINT NOT NULL,
    command_type    VARCHAR(16) NOT NULL,
    command_data    JSONB NOT NULL,

    range_valid     BOOLEAN DEFAULT TRUE,
    rate_valid      BOOLEAN DEFAULT TRUE,

    sent_at         TIMESTAMP,
    relayed_at      TIMESTAMP,
    received_at     TIMESTAMP,
    executed_at     TIMESTAMP,

    network_latency_ms   INTEGER,
    execution_latency_ms INTEGER,
    total_latency_ms     INTEGER
);

CREATE INDEX IF NOT EXISTS idx_commands_session ON control_commands(session_id, sequence);
