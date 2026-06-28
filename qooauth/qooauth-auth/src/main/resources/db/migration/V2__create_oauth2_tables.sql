-- OAuth 2.0 / OIDC Provider tables
-- Registered OAuth2 clients (RP / third-party apps)
CREATE TABLE IF NOT EXISTS oauth2_clients (
    client_id       VARCHAR(64) PRIMARY KEY,
    client_secret   VARCHAR(255),
    client_name     VARCHAR(128) NOT NULL,
    redirect_uris   TEXT NOT NULL,             -- JSON array of allowed redirect URIs
    grant_types     VARCHAR(255) NOT NULL,      -- e.g. "authorization_code,refresh_token,client_credentials"
    scopes          VARCHAR(512) NOT NULL DEFAULT 'openid profile email',
    token_endpoint_auth_method VARCHAR(32) DEFAULT 'client_secret_basic',
    require_pkce    BOOLEAN DEFAULT TRUE,
    require_consent BOOLEAN DEFAULT TRUE,
    logo_uri        VARCHAR(512),
    homepage_uri    VARCHAR(512),
    policy_uri      VARCHAR(512),
    tos_uri         VARCHAR(512),
    owner_user_id   VARCHAR(32),               -- FK to users.user_id (developer who registered)
    enabled         BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_oauth2_clients_owner ON oauth2_clients(owner_user_id);

-- Authorization codes (short-lived, single-use)
CREATE TABLE IF NOT EXISTS oauth2_authorization_codes (
    code            VARCHAR(128) PRIMARY KEY,
    client_id       VARCHAR(64) NOT NULL,
    user_id         VARCHAR(32) NOT NULL,       -- FK to users.user_id
    redirect_uri    VARCHAR(512) NOT NULL,
    scopes          VARCHAR(512) NOT NULL,
    code_challenge  VARCHAR(128),               -- PKCE S256 challenge
    code_challenge_method VARCHAR(16) DEFAULT 'S256',
    nonce           VARCHAR(128),               -- OIDC nonce
    state           VARCHAR(512),
    expires_at      TIMESTAMPTZ NOT NULL,
    used            BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_oauth2_auth_codes_expires ON oauth2_authorization_codes(expires_at);

-- Refresh tokens issued to OAuth2 clients
CREATE TABLE IF NOT EXISTS oauth2_refresh_tokens (
    token           VARCHAR(128) PRIMARY KEY,
    client_id       VARCHAR(64) NOT NULL,
    user_id         VARCHAR(32) NOT NULL,
    scopes          VARCHAR(512) NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_oauth2_refresh_tokens_user ON oauth2_refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_oauth2_refresh_tokens_client ON oauth2_refresh_tokens(client_id);

-- OAuth2 consent records
CREATE TABLE IF NOT EXISTS oauth2_consents (
    id              BIGSERIAL PRIMARY KEY,
    client_id       VARCHAR(64) NOT NULL,
    user_id         VARCHAR(32) NOT NULL,
    scopes          VARCHAR(512) NOT NULL,
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,                -- NULL = permanent
    revoked         BOOLEAN DEFAULT FALSE,
    UNIQUE(client_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_oauth2_consents_user ON oauth2_consents(user_id);
