-- V13: Robot Trust Infrastructure
-- Robot-to-robot trust groups, membership, and collaboration delegation

CREATE TABLE IF NOT EXISTS robot_trust_groups (
    group_id        VARCHAR(64)     PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL,
    description     TEXT,
    owner_user_id   VARCHAR(64)     NOT NULL,
    state           VARCHAR(16)     NOT NULL DEFAULT 'ACTIVE',
    max_members     INTEGER         DEFAULT 50,
    trust_policy    TEXT,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dissolved_at    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS robot_group_memberships (
    membership_id       VARCHAR(64)     PRIMARY KEY,
    group_id            VARCHAR(64)     NOT NULL REFERENCES robot_trust_groups(group_id),
    device_id           VARCHAR(64)     NOT NULL,
    user_id             VARCHAR(64),
    role                VARCHAR(16)     NOT NULL DEFAULT 'MEMBER',
    state               VARCHAR(16)     NOT NULL DEFAULT 'ACTIVE',
    capability_grants   TEXT,
    joined_at           TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    left_at             TIMESTAMP,
    CONSTRAINT uk_rgm_group_device UNIQUE (group_id, device_id)
);

CREATE TABLE IF NOT EXISTS collaboration_delegations (
    delegation_id           VARCHAR(64)     PRIMARY KEY,
    token_hash              VARCHAR(128)    NOT NULL UNIQUE,
    delegator_device_id     VARCHAR(64)     NOT NULL,
    delegator_user_id       VARCHAR(64),
    delegate_device_id      VARCHAR(64)     NOT NULL,
    delegate_user_id        VARCHAR(64),
    capabilities            TEXT            NOT NULL,
    state                   VARCHAR(16)     NOT NULL DEFAULT 'ACTIVE',
    issued_at               TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at              TIMESTAMP       NOT NULL,
    revoked_at              TIMESTAMP,
    revoke_reason           VARCHAR(256),
    created_at              TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_rtg_owner ON robot_trust_groups(owner_user_id);
CREATE INDEX idx_rtg_state ON robot_trust_groups(state);
CREATE INDEX idx_rgm_group ON robot_group_memberships(group_id);
CREATE INDEX idx_rgm_device ON robot_group_memberships(device_id);
CREATE INDEX idx_rgm_state ON robot_group_memberships(state);
CREATE INDEX idx_cd_delegator ON collaboration_delegations(delegator_device_id);
CREATE INDEX idx_cd_delegate ON collaboration_delegations(delegate_device_id);
CREATE INDEX idx_cd_token_hash ON collaboration_delegations(token_hash);
CREATE INDEX idx_cd_expires ON collaboration_delegations(expires_at);
