-- V10: RBAC (Role-Based Access Control) Tables
-- Supports: roles, permissions, resource-level access control

-- Roles table (system-defined + custom roles)
CREATE TABLE IF NOT EXISTS roles (
    id              BIGSERIAL       PRIMARY KEY,
    role_id         VARCHAR(64)     NOT NULL UNIQUE,   -- e.g. "ADMIN", "DEVELOPER", "DEVICE_OPERATOR"
    name            VARCHAR(128)    NOT NULL,
    description     TEXT,
    category        VARCHAR(32)     NOT NULL DEFAULT 'CUSTOM',
    -- SYSTEM / FAMILY / ENTERPRISE / CUSTOM
    is_system       BOOLEAN         NOT NULL DEFAULT FALSE,
    parent_role_id  VARCHAR(64)     REFERENCES roles(role_id) ON DELETE SET NULL,
    priority        INT             NOT NULL DEFAULT 0, -- higher = more privileged
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_roles_category ON roles(category);

-- Permissions table (granular resource-level permissions)
CREATE TABLE IF NOT EXISTS permissions (
    id              BIGSERIAL       PRIMARY KEY,
    permission_id   VARCHAR(128)    NOT NULL UNIQUE,    -- e.g. "device:read", "device:control", "user:manage"
    name            VARCHAR(255)    NOT NULL,
    description     TEXT,
    resource_type   VARCHAR(64)     NOT NULL,           -- device / user / skill / audit / api_key
    action          VARCHAR(64)     NOT NULL,           -- read / write / delete / manage / control
    scope           VARCHAR(32)     NOT NULL DEFAULT 'OWNED',
    -- OWNED (own resources only) / GROUP (group resources) / ALL (all resources)
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_permissions_resource ON permissions(resource_type, action);

-- Role-to-permission mapping (many-to-many)
CREATE TABLE IF NOT EXISTS role_permissions (
    id              BIGSERIAL       PRIMARY KEY,
    role_id         VARCHAR(64)     NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    permission_id   VARCHAR(128)    NOT NULL REFERENCES permissions(permission_id) ON DELETE CASCADE,
    granted_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE (role_id, permission_id)
);

CREATE INDEX idx_role_permissions_role ON role_permissions(role_id);
CREATE INDEX idx_role_permissions_perm ON role_permissions(permission_id);

-- User-to-role assignments
CREATE TABLE IF NOT EXISTS user_roles (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         VARCHAR(32)     NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role_id         VARCHAR(64)     NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    scope_type      VARCHAR(32)     DEFAULT NULL,       -- null = global, or resource type for scoped roles
    scope_id        VARCHAR(64)     DEFAULT NULL,       -- null = global, or resource id
    granted_by      VARCHAR(32)     REFERENCES users(user_id),
    granted_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,                        -- NULL = permanent
    UNIQUE (user_id, role_id, scope_type, scope_id)
);

CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);

-- Permission audit log for access decisions
CREATE TABLE IF NOT EXISTS access_decisions (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         VARCHAR(32)     REFERENCES users(user_id),
    permission_id   VARCHAR(128)    NOT NULL,
    resource_type   VARCHAR(64)     NOT NULL,
    resource_id     VARCHAR(64),
    action          VARCHAR(64)     NOT NULL,
    decision        VARCHAR(16)     NOT NULL,           -- ALLOW / DENY
    reason          VARCHAR(255),                       -- reason for deny
    ip_address      VARCHAR(45),
    user_agent      TEXT,
    decided_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_access_decisions_user ON access_decisions(user_id);
CREATE INDEX idx_access_decisions_time ON access_decisions(decided_at DESC);

-- =============================================
-- Seed default system roles and permissions
-- =============================================

-- System roles
INSERT INTO roles (role_id, name, description, category, is_system, priority) VALUES
('SUPER_ADMIN', 'Super Administrator', 'Full system access, all resources', 'SYSTEM', TRUE, 1000),
('ADMIN', 'Administrator', 'Administrative access, manage users and devices', 'SYSTEM', TRUE, 800),
('DEVELOPER', 'Developer', 'Developer access, API keys, skill management', 'SYSTEM', TRUE, 600),
('DEVICE_OPERATOR', 'Device Operator', 'Device control and monitoring', 'SYSTEM', TRUE, 400),
('USER', 'Standard User', 'Basic user access, own resources only', 'SYSTEM', TRUE, 200),
('GUEST', 'Guest', 'Read-only access to shared resources', 'SYSTEM', TRUE, 100)
ON CONFLICT (role_id) DO NOTHING;

-- Permission definitions (resource:action)
INSERT INTO permissions (permission_id, name, description, resource_type, action, scope) VALUES
-- User management
('user:read', 'Read User', 'View user profile information', 'user', 'read', 'OWNED'),
('user:read_all', 'Read All Users', 'View all user profiles', 'user', 'read', 'ALL'),
('user:write', 'Write User', 'Update own profile', 'user', 'write', 'OWNED'),
('user:manage', 'Manage Users', 'Create/update/delete any user', 'user', 'manage', 'ALL'),
-- Device management
('device:read', 'Read Device', 'View own device information', 'device', 'read', 'OWNED'),
('device:read_all', 'Read All Devices', 'View all devices', 'device', 'read', 'ALL'),
('device:control', 'Control Device', 'Send commands to own devices', 'device', 'control', 'OWNED'),
('device:manage', 'Manage Devices', 'Full device management', 'device', 'manage', 'ALL'),
-- API Key management
('api_key:read', 'Read API Keys', 'View own API keys', 'api_key', 'read', 'OWNED'),
('api_key:manage', 'Manage API Keys', 'Create/revoke API keys', 'api_key', 'manage', 'OWNED'),
('api_key:manage_all', 'Manage All API Keys', 'Manage all API keys', 'api_key', 'manage', 'ALL'),
-- Audit
('audit:read', 'Read Audit Logs', 'View own audit events', 'audit', 'read', 'OWNED'),
('audit:read_all', 'Read All Audit Logs', 'View all audit events', 'audit', 'read', 'ALL'),
('audit:export', 'Export Audit Logs', 'Export audit data', 'audit', 'write', 'ALL'),
-- Skill management
('skill:read', 'Read Skills', 'View skill information', 'skill', 'read', 'ALL'),
('skill:write', 'Write Skills', 'Create/update own skills', 'skill', 'write', 'OWNED'),
('skill:manage', 'Manage Skills', 'Full skill management', 'skill', 'manage', 'ALL'),
-- System
('system:config', 'System Configuration', 'View/update system config', 'system', 'manage', 'ALL'),
('system:health', 'System Health', 'View system health metrics', 'system', 'read', 'ALL'),
('role:manage', 'Manage Roles', 'Create/update/delete roles', 'role', 'manage', 'ALL')
ON CONFLICT (permission_id) DO NOTHING;

-- Role-to-permission assignments
-- SUPER_ADMIN: all permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT 'SUPER_ADMIN', permission_id FROM permissions
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- ADMIN: most permissions except super-admin specific
INSERT INTO role_permissions (role_id, permission_id) VALUES
('ADMIN', 'user:read_all'), ('ADMIN', 'user:manage'),
('ADMIN', 'device:read_all'), ('ADMIN', 'device:manage'),
('ADMIN', 'api_key:manage_all'), ('ADMIN', 'audit:read_all'),
('ADMIN', 'audit:export'), ('ADMIN', 'skill:manage'),
('ADMIN', 'system:config'), ('ADMIN', 'system:health'),
('ADMIN', 'role:manage')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- DEVELOPER
INSERT INTO role_permissions (role_id, permission_id) VALUES
('DEVELOPER', 'user:read'), ('DEVELOPER', 'user:write'),
('DEVELOPER', 'device:read'), ('DEVELOPER', 'device:control'),
('DEVELOPER', 'api_key:read'), ('DEVELOPER', 'api_key:manage'),
('DEVELOPER', 'audit:read'), ('DEVELOPER', 'skill:read'),
('DEVELOPER', 'skill:write'), ('DEVELOPER', 'system:health')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- DEVICE_OPERATOR
INSERT INTO role_permissions (role_id, permission_id) VALUES
('DEVICE_OPERATOR', 'user:read'), ('DEVICE_OPERATOR', 'device:read'),
('DEVICE_OPERATOR', 'device:control'), ('DEVICE_OPERATOR', 'audit:read'),
('DEVICE_OPERATOR', 'skill:read'), ('DEVICE_OPERATOR', 'system:health')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- USER (default)
INSERT INTO role_permissions (role_id, permission_id) VALUES
('USER', 'user:read'), ('USER', 'user:write'),
('USER', 'device:read'), ('USER', 'device:control'),
('USER', 'api_key:read'), ('USER', 'api_key:manage'),
('USER', 'audit:read'), ('USER', 'skill:read')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- GUEST
INSERT INTO role_permissions (role_id, permission_id) VALUES
('GUEST', 'user:read'), ('GUEST', 'device:read'),
('GUEST', 'skill:read')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Assign all existing users to USER role (default)
INSERT INTO user_roles (user_id, role_id)
SELECT user_id, 'USER' FROM users
WHERE state NOT IN ('DELETED')
ON CONFLICT (user_id, role_id, scope_type, scope_id) DO NOTHING;
