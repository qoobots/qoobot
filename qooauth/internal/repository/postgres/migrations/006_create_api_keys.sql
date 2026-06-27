-- 006: API 密钥表
-- 开发者/企业 API Key 管理

CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_prefix      VARCHAR(16) NOT NULL,     -- "qoo_sk_" + 前 8 字符
    key_hash        VARCHAR(128) NOT NULL,    -- SHA-512(API Key)
    key_name        VARCHAR(100) NOT NULL,
    scopes          TEXT[] NOT NULL,
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_apikeys_user ON api_keys(user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_apikeys_hash ON api_keys(key_hash);
