-- ============================================================
-- qooauth Initial Seed Data
-- ============================================================
-- Inserts default OAuth2 clients, roles, and configuration data.
-- Run after database initialization and Flyway migrations.
--
-- Usage: psql -h localhost -U qooauth -d qooauth -f seed-data.sql
-- ============================================================

BEGIN;

-- ============================================================
-- 1. Default Roles
-- ============================================================
INSERT INTO roles (role_id, name, description, created_at) VALUES
    ('role_admin_001', 'ROLE_ADMIN', 'System administrator with full access', NOW()),
    ('role_user_001', 'ROLE_USER', 'Standard authenticated user', NOW()),
    ('role_developer_001', 'ROLE_DEVELOPER', 'Developer with sandbox and cert access', NOW()),
    ('role_device_001', 'ROLE_DEVICE', 'Robot/device identity', NOW()),
    ('role_auditor_001', 'ROLE_AUDITOR', 'Audit log viewer', NOW()),
    ('role_api_001', 'ROLE_API', 'API key authenticated access', NOW())
ON CONFLICT (role_id) DO NOTHING;

-- ============================================================
-- 2. Default OAuth2 Clients
-- ============================================================
-- IMPORTANT: Change client secrets in production!
-- Secret hashes below are for 'change-me-in-production' (SHA-256 base64)

INSERT INTO oauth2_clients (
    client_id, client_secret_hash, client_name,
    grant_types, redirect_uris, scopes,
    access_token_ttl_seconds, refresh_token_ttl_seconds,
    state, created_at
) VALUES
    -- Web Portal Client (Authorization Code + PKCE)
    (
        'qoobot-web-portal',
        'XohImNooBHFR0OVvjcYpJ3NgPQ1qq73WKhHvch0VQtg=',
        'QooBot Web Portal',
        'authorization_code,refresh_token',
        'http://localhost:3000/callback,https://qoobot.io/callback',
        'openid,profile,email,offline_access',
        3600, 2592000,
        'ACTIVE', NOW()
    ),
    -- Mobile App Client
    (
        'qoobot-mobile-app',
        'XohImNooBHFR0OVvjcYpJ3NgPQ1qq73WKhHvch0VQtg=',
        'QooBot Mobile App',
        'authorization_code,refresh_token',
        'qoobot://callback,com.qoobot.app://callback',
        'openid,profile,email,offline_access',
        3600, 2592000,
        'ACTIVE', NOW()
    ),
    -- Desktop Console Client
    (
        'qoobot-desktop-console',
        'XohImNooBHFR0OVvjcYpJ3NgPQ1qq73WKhHvch0VQtg=',
        'QooBot Desktop Console',
        'authorization_code,refresh_token',
        'http://localhost:8089/callback',
        'openid,profile,email,device:read,device:write,offline_access',
        3600, 2592000,
        'ACTIVE', NOW()
    ),
    -- Machine-to-Machine Client (Client Credentials)
    (
        'qoobot-m2m-service',
        'XohImNooBHFR0OVvjcYpJ3NgPQ1qq73WKhHvch0VQtg=',
        'QooBot M2M Service Account',
        'client_credentials',
        '',
        'device:read,device:write,user:read,audit:read',
        3600, 0,
        'ACTIVE', NOW()
    ),
    -- Device Registration Client
    (
        'qoobot-device-registration',
        'XohImNooBHFR0OVvjcYpJ3NgPQ1qq73WKhHvch0VQtg=',
        'QooBot Device Registration',
        'client_credentials',
        '',
        'device:register,device:certificate',
        1800, 0,
        'ACTIVE', NOW()
    ),
    -- Mini Program Client
    (
        'qoobot-mini-program',
        'XohImNooBHFR0OVvjcYpJ3NgPQ1qq73WKhHvch0VQtg=',
        'QooBot Mini Program',
        'authorization_code,refresh_token',
        'https://miniprogram.qoobot.io/callback',
        'openid,profile,email,offline_access',
        3600, 2592000,
        'ACTIVE', NOW()
    )
ON CONFLICT (client_id) DO NOTHING;

-- ============================================================
-- 3. Default OAuth2 Scopes
-- ============================================================
INSERT INTO oauth2_scopes (scope_id, name, description, is_default, created_at) VALUES
    ('scope_openid', 'openid', 'OpenID Connect authentication', true, NOW()),
    ('scope_profile', 'profile', 'Access to basic profile information', true, NOW()),
    ('scope_email', 'email', 'Access to email address', false, NOW()),
    ('scope_offline_access', 'offline_access', 'Issue refresh token for offline access', false, NOW()),
    ('scope_device_read', 'device:read', 'Read device information', false, NOW()),
    ('scope_device_write', 'device:write', 'Manage devices', false, NOW()),
    ('scope_user_read', 'user:read', 'Read user information', false, NOW()),
    ('scope_user_write', 'user:write', 'Manage users', false, NOW()),
    ('scope_audit_read', 'audit:read', 'Read audit logs', false, NOW()),
    ('scope_admin', 'admin', 'Administrative access', false, NOW())
ON CONFLICT (scope_id) DO NOTHING;

-- ============================================================
-- 4. Default System Configuration
-- ============================================================
INSERT INTO system_config (config_key, config_value, description, created_at) VALUES
    ('auth.session.max_concurrent', '5', 'Maximum concurrent sessions per user', NOW()),
    ('auth.token.access_ttl', '3600', 'Default access token TTL in seconds', NOW()),
    ('auth.token.refresh_ttl', '2592000', 'Default refresh token TTL in seconds (30 days)', NOW()),
    ('auth.password.min_length', '8', 'Minimum password length', NOW()),
    ('auth.password.require_special', 'true', 'Require special characters in passwords', NOW()),
    ('auth.mfa.enabled', 'true', 'Enable multi-factor authentication', NOW()),
    ('auth.lockout.max_attempts', '5', 'Maximum failed login attempts before lockout', NOW()),
    ('auth.lockout.duration_minutes', '15', 'Account lockout duration in minutes', NOW()),
    ('device.certificate.default_ttl_days', '365', 'Default device certificate TTL in days', NOW()),
    ('device.max_per_user', '50', 'Maximum devices per user', NOW()),
    ('api_key.max_per_user', '20', 'Maximum API keys per user', NOW()),
    ('api_key.default_ttl_days', '365', 'Default API key TTL in days', NOW()),
    ('rate_limit.default_capacity', '100', 'Default rate limit token bucket capacity', NOW()),
    ('rate_limit.default_refill_rate', '10', 'Default rate limit refill rate per second', NOW()),
    ('audit.retention_days', '365', 'Audit log retention period in days', NOW()),
    ('sandbox.default_ttl_seconds', '3600', 'Default developer sandbox TTL', NOW()),
    ('sandbox.max_per_user', '3', 'Maximum sandboxes per developer', NOW())
ON CONFLICT (config_key) DO NOTHING;

-- ============================================================
-- 5. Default Admin User (for initial setup)
-- ============================================================
-- Password: Admin@123! (bcrypt hash - CHANGE IN PRODUCTION!)
INSERT INTO users (
    user_id, email, display_name, password_hash,
    state, email_verified, created_at
) VALUES (
    'admin_root_001',
    'admin@qoobot.io',
    'System Administrator',
    '$2a$12$LJ3m4ys3Lk0TSwHCpNqrEeYpMiSSwHBxYsNymdFJhBB7rZpPRmDGi',
    'ACTIVE', true, NOW()
) ON CONFLICT (user_id) DO NOTHING;

-- Assign admin role to admin user
INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES
    ('admin_root_001', 'role_admin_001', NOW())
ON CONFLICT DO NOTHING;

-- ============================================================
-- 6. Default Robot Trust Group (for testing)
-- ============================================================
INSERT INTO robot_trust_groups (
    group_id, name, owner_device_id, trust_policy, state, created_at
) VALUES (
    'default_trust_group',
    'Default Robot Fleet',
    'admin_root_001',
    '{"max_members": 100, "require_mtls": true, "token_ttl_seconds": 3600, "auto_join": false}'::jsonb,
    'ACTIVE', NOW()
) ON CONFLICT (group_id) DO NOTHING;

COMMIT;

-- ============================================================
-- Verification queries (uncomment to verify seed data)
-- ============================================================
-- SELECT COUNT(*) AS role_count FROM roles;
-- SELECT COUNT(*) AS client_count FROM oauth2_clients;
-- SELECT COUNT(*) AS scope_count FROM oauth2_scopes;
-- SELECT COUNT(*) AS config_count FROM system_config;
-- SELECT email, display_name, state FROM users;
