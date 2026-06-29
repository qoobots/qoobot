-- qoocommunity v0.2 Additional Tables
-- PostgreSQL 16

-- ============================================================
-- CLA 签署记录
-- ============================================================
CREATE TABLE IF NOT EXISTS cla_records (
    id          BIGSERIAL PRIMARY KEY,
    user_id     VARCHAR(64) NOT NULL,
    cla_version VARCHAR(20),
    cla_type    VARCHAR(20),
    signed_at   TIMESTAMP,
    ip_address  VARCHAR(45),
    user_agent  VARCHAR(512),
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cla_records_user ON cla_records(user_id, signed_at DESC);

-- ============================================================
-- SIG 成员
-- ============================================================
CREATE TABLE IF NOT EXISTS governance_sig_members (
    id          BIGSERIAL PRIMARY KEY,
    sig_id      BIGINT NOT NULL REFERENCES governance_sigs(id) ON DELETE CASCADE,
    user_id     VARCHAR(64) NOT NULL,
    role        VARCHAR(50) DEFAULT 'MEMBER',
    joined_at   TIMESTAMP DEFAULT NOW(),
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE(sig_id, user_id)
);

CREATE INDEX idx_sig_members_sig ON governance_sig_members(sig_id);
CREATE INDEX idx_sig_members_user ON governance_sig_members(user_id);

-- ============================================================
-- 学习路径
-- ============================================================
CREATE TABLE IF NOT EXISTS academy_learning_paths (
    id          BIGSERIAL PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    slug        VARCHAR(100),
    description TEXT,
    cover_url   VARCHAR(512),
    level       VARCHAR(20),
    course_count INT DEFAULT 0,
    sort_order  INT DEFAULT 0,
    is_published BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- 课时学习进度
-- ============================================================
CREATE TABLE IF NOT EXISTS academy_lesson_progress (
    id          BIGSERIAL PRIMARY KEY,
    user_id     VARCHAR(64) NOT NULL,
    lesson_id   BIGINT NOT NULL REFERENCES academy_lessons(id) ON DELETE CASCADE,
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    created_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, lesson_id)
);

CREATE INDEX idx_lesson_progress_user ON academy_lesson_progress(user_id);
