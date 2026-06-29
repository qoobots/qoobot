-- V15: Family Sharing & Organization Management
-- Family groups, members, parental controls, organization profiles, MDM

CREATE TABLE IF NOT EXISTS family_groups (
    family_id           VARCHAR(64)     PRIMARY KEY,
    name                VARCHAR(128)    NOT NULL,
    organizer_user_id   VARCHAR(64)     NOT NULL,
    state               VARCHAR(16)     NOT NULL DEFAULT 'ACTIVE',
    max_members         INTEGER         DEFAULT 6,
    sharing_settings    TEXT,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS family_members (
    member_id           VARCHAR(64)     PRIMARY KEY,
    family_id           VARCHAR(64)     NOT NULL REFERENCES family_groups(family_id),
    user_id             VARCHAR(64)     NOT NULL,
    role                VARCHAR(16)     NOT NULL,
    state               VARCHAR(16)     NOT NULL DEFAULT 'ACTIVE',
    parental_controls   TEXT,
    joined_at           TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_fm_family_user UNIQUE (family_id, user_id)
);

CREATE TABLE IF NOT EXISTS organization_profiles (
    org_id              VARCHAR(64)     PRIMARY KEY,
    name                VARCHAR(256)    NOT NULL,
    admin_user_id       VARCHAR(64)     NOT NULL,
    state               VARCHAR(16)     NOT NULL DEFAULT 'ACTIVE',
    mdm_config          TEXT,
    max_devices         INTEGER         DEFAULT 100,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fg_organizer ON family_groups(organizer_user_id);
CREATE INDEX IF NOT EXISTS idx_fg_state ON family_groups(state);
CREATE INDEX IF NOT EXISTS idx_fm_family ON family_members(family_id);
CREATE INDEX IF NOT EXISTS idx_fm_user ON family_members(user_id);
CREATE INDEX IF NOT EXISTS idx_op_admin ON organization_profiles(admin_user_id);
CREATE INDEX IF NOT EXISTS idx_op_state ON organization_profiles(state);
