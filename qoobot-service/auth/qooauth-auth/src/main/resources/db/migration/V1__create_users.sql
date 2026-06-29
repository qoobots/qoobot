CREATE TABLE IF NOT EXISTS users (
    user_id         VARCHAR(32) PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    phone           VARCHAR(20),
    password_hash   VARCHAR(255) NOT NULL,
    password_salt   VARCHAR(64) NOT NULL,
    nickname        VARCHAR(64) NOT NULL,
    avatar_hash     VARCHAR(64),
    language        VARCHAR(10) DEFAULT 'zh-CN',
    timezone        VARCHAR(50) DEFAULT 'Asia/Shanghai',
    state           VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    email_verified  BOOLEAN DEFAULT FALSE,
    phone_verified  BOOLEAN DEFAULT FALSE,
    mfa_enabled     BOOLEAN DEFAULT FALSE,
    mfa_methods     JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE state != 'DELETED';
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone ON users(phone) WHERE state != 'DELETED' AND phone IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_state ON users(state);
CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at);
