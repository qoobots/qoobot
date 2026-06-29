-- ============================================================
-- V4: Governance seed data & schema amendments
-- PostgreSQL 16
-- ============================================================

-- ============================================================
-- Schema Amendments: Add missing columns for seed data
-- ============================================================

-- governance_tsc_members: add name, bio, avatar_url, github, sort_order columns
ALTER TABLE governance_tsc_members
    ADD COLUMN IF NOT EXISTS name       VARCHAR(200),
    ADD COLUMN IF NOT EXISTS bio        TEXT,
    ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(512),
    ADD COLUMN IF NOT EXISTS github     VARCHAR(200),
    ADD COLUMN IF NOT EXISTS sort_order INT DEFAULT 0;

-- governance_sigs: add lead_user_id, is_active columns; rename chair_id if needed
ALTER TABLE governance_sigs
    ADD COLUMN IF NOT EXISTS lead_user_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS is_active    BOOLEAN DEFAULT TRUE;

-- ============================================================
-- TSC Members
-- ============================================================
INSERT INTO governance_tsc_members (user_id, name, role, bio, avatar_url, github, sort_order, is_active, term_start, term_end, created_at)
VALUES
('u-changli',   'Chang Li',   'CHAIR',      'QooBot 创始人兼 CEO，机器人操作系统架构师',            '/images/team/changli.png',   'changli',   1, TRUE, '2024-01-01', '2026-12-31', NOW()),
('u-alexchen',  'Alex Chen',  'VICE_CHAIR', '前 ROS 核心贡献者，SLAM 算法专家',                       '/images/team/alexchen.png',  'alexchen',  2, TRUE, '2024-01-01', '2026-12-31', NOW()),
('u-sarahwang', 'Sarah Wang', 'MEMBER',     'AI 感知团队负责人，CVPR/ICCV 领域主席',                   '/images/team/sarahwang.png', 'sarahwang', 3, TRUE, '2024-01-01', '2026-12-31', NOW()),
('u-ryansmith', 'Ryan Smith', 'MEMBER',     '硬件架构总监，前 Apple 硬件工程师',                       '/images/team/ryansmith.png', 'ryansmith', 4, TRUE, '2024-01-01', '2026-12-31', NOW()),
('u-emmali',    'Emma Li',    'MEMBER',     '社区运营总监，开源治理专家',                              '/images/team/emmali.png',    'emmali',    5, TRUE, '2024-01-01', '2026-12-31', NOW())
ON CONFLICT (user_id) DO NOTHING;

-- ============================================================
-- SIGs
-- ============================================================
INSERT INTO governance_sigs (name, slug, description, lead_user_id, member_count, is_active, created_at)
VALUES
('感知与视觉',       'perception-vision',  '聚焦机器人视觉感知、SLAM、3D 重建等方向',           'u-sarahwang', 23, TRUE, NOW()),
('运动规划与控制',   'motion-control',     '运动规划、全身控制、力控算法研究与实现',             'u-alexchen',  18, TRUE, NOW()),
('人机交互',         'hri',                '人机交互设计、语音对话、表情系统、AR/VR 集成',      'u-emmali',    15, TRUE, NOW()),
('硬件与嵌入式',     'hardware-embedded',  '计算平台、传感器模组、执行器、BMS 硬件设计',        'u-ryansmith', 20, TRUE, NOW()),
('开发者工具',       'dev-tools',          'IDE 插件、仿真器、调试工具、CI/CD 流水线',          'u-changli',   12, TRUE, NOW()),
('技能生态',         'skill-ecosystem',    '技能 SDK、应用开发规范、技能审核与发布',             'u-emmali',    16, TRUE, NOW())
ON CONFLICT (slug) DO NOTHING;

-- ============================================================
-- SIG Members (CHAIR for each SIG)
-- ============================================================
INSERT INTO governance_sig_members (sig_id, user_id, role, joined_at, created_at, updated_at)
SELECT s.id, 'u-sarahwang', 'CHAIR', NOW(), NOW(), NOW() FROM governance_sigs s WHERE s.slug = 'perception-vision'
ON CONFLICT (sig_id, user_id) DO NOTHING;

INSERT INTO governance_sig_members (sig_id, user_id, role, joined_at, created_at, updated_at)
SELECT s.id, 'u-alexchen', 'CHAIR', NOW(), NOW(), NOW() FROM governance_sigs s WHERE s.slug = 'motion-control'
ON CONFLICT (sig_id, user_id) DO NOTHING;

INSERT INTO governance_sig_members (sig_id, user_id, role, joined_at, created_at, updated_at)
SELECT s.id, 'u-emmali', 'CHAIR', NOW(), NOW(), NOW() FROM governance_sigs s WHERE s.slug = 'hri'
ON CONFLICT (sig_id, user_id) DO NOTHING;

INSERT INTO governance_sig_members (sig_id, user_id, role, joined_at, created_at, updated_at)
SELECT s.id, 'u-ryansmith', 'CHAIR', NOW(), NOW(), NOW() FROM governance_sigs s WHERE s.slug = 'hardware-embedded'
ON CONFLICT (sig_id, user_id) DO NOTHING;

INSERT INTO governance_sig_members (sig_id, user_id, role, joined_at, created_at, updated_at)
SELECT s.id, 'u-changli', 'CHAIR', NOW(), NOW(), NOW() FROM governance_sigs s WHERE s.slug = 'dev-tools'
ON CONFLICT (sig_id, user_id) DO NOTHING;

INSERT INTO governance_sig_members (sig_id, user_id, role, joined_at, created_at, updated_at)
SELECT s.id, 'u-emmali', 'CHAIR', NOW(), NOW(), NOW() FROM governance_sigs s WHERE s.slug = 'skill-ecosystem'
ON CONFLICT (sig_id, user_id) DO NOTHING;
