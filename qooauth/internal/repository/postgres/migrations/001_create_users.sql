-- 001: 用户主表
-- 对标 Apple ID，管理所有 QooBot 用户账户

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    phone           VARCHAR(32),
    phone_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    password_hash   VARCHAR(128),           -- argon2id hash, 可为 NULL (Passkey 用户)
    display_name    VARCHAR(100) NOT NULL,
    avatar_url      VARCHAR(512),
    locale          VARCHAR(10) NOT NULL DEFAULT 'en-US',
    timezone        VARCHAR(64) NOT NULL DEFAULT 'UTC',
    totp_enabled    BOOLEAN NOT NULL DEFAULT FALSE,
    totp_secret     TEXT,                    -- AES-256-GCM 加密存储
    passkey_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    account_status  VARCHAR(16) NOT NULL DEFAULT 'active'
                    CHECK (account_status IN ('active', 'locked', 'suspended', 'deleted')),
    locked_until    TIMESTAMPTZ,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ              -- 软删除
);

CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_status ON users(account_status);

-- 自动更新 updated_at 触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
