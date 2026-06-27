-- 004: 审计日志表
-- 全量操作审计，支持按月分区

CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID,
    action          VARCHAR(64) NOT NULL,
    resource_type   VARCHAR(32) NOT NULL,
    resource_id     VARCHAR(128),
    details         JSONB,
    ip_address      INET NOT NULL,
    user_agent      VARCHAR(512),
    success         BOOLEAN NOT NULL,
    error_code      VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_action ON audit_logs(action, created_at DESC);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);
