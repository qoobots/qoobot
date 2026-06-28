-- qoocommunity v0.1 Initial Schema
-- PostgreSQL 16

-- ============================================================
-- 用户扩展
-- ============================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    id          BIGSERIAL PRIMARY KEY,
    user_id     VARCHAR(64)  NOT NULL UNIQUE,
    nickname    VARCHAR(100) NOT NULL,
    avatar_url  VARCHAR(512),
    bio         TEXT,
    company     VARCHAR(200),
    title       VARCHAR(200),
    location    VARCHAR(200),
    website     VARCHAR(512),
    github      VARCHAR(200),
    reputation  INT DEFAULT 0,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_profiles_user_id ON user_profiles(user_id);
CREATE INDEX idx_profiles_reputation ON user_profiles(reputation DESC);

-- ============================================================
-- 贡献者
-- ============================================================
CREATE TABLE IF NOT EXISTS contributors (
    id              BIGSERIAL PRIMARY KEY,
    user_id         VARCHAR(64) NOT NULL UNIQUE,
    cla_signed      BOOLEAN DEFAULT FALSE,
    cla_signed_at   TIMESTAMP,
    cla_type        VARCHAR(20),
    level           VARCHAR(20) DEFAULT 'CONTRIBUTOR',
    pr_count        INT DEFAULT 0,
    commit_count    INT DEFAULT 0,
    review_count    INT DEFAULT 0,
    active_months   INT DEFAULT 0,
    joined_at       TIMESTAMP DEFAULT NOW(),
    promoted_at     TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_contributors_user ON contributors(user_id);
CREATE INDEX idx_contributors_level ON contributors(level);

-- ============================================================
-- 论坛分类
-- ============================================================
CREATE TABLE IF NOT EXISTS forum_categories (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    slug        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    sort_order  INT DEFAULT 0,
    parent_id   BIGINT REFERENCES forum_categories(id),
    topic_count INT DEFAULT 0,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- 论坛标签
-- ============================================================
CREATE TABLE IF NOT EXISTS forum_tags (
    id      BIGSERIAL PRIMARY KEY,
    name    VARCHAR(50) NOT NULL UNIQUE,
    slug    VARCHAR(50) NOT NULL UNIQUE,
    color   VARCHAR(7),
    topic_count INT DEFAULT 0
);

-- ============================================================
-- 论坛帖子
-- ============================================================
CREATE TABLE IF NOT EXISTS forum_topics (
    id              BIGSERIAL PRIMARY KEY,
    category_id     BIGINT NOT NULL REFERENCES forum_categories(id),
    user_id         VARCHAR(64) NOT NULL,
    title           VARCHAR(500) NOT NULL,
    content         TEXT NOT NULL,
    content_html    TEXT NOT NULL,
    is_pinned       BOOLEAN DEFAULT FALSE,
    is_locked       BOOLEAN DEFAULT FALSE,
    view_count      INT DEFAULT 0,
    reply_count     INT DEFAULT 0,
    like_count      INT DEFAULT 0,
    last_reply_at   TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_topics_category ON forum_topics(category_id, created_at DESC);
CREATE INDEX idx_topics_user ON forum_topics(user_id);

-- ============================================================
-- 论坛回复
-- ============================================================
CREATE TABLE IF NOT EXISTS forum_replies (
    id          BIGSERIAL PRIMARY KEY,
    topic_id    BIGINT NOT NULL REFERENCES forum_topics(id) ON DELETE CASCADE,
    user_id     VARCHAR(64) NOT NULL,
    parent_id   BIGINT REFERENCES forum_replies(id),
    content     TEXT NOT NULL,
    content_html TEXT NOT NULL,
    like_count  INT DEFAULT 0,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_replies_topic ON forum_replies(topic_id, created_at ASC);

-- ============================================================
-- 帖子-标签关联
-- ============================================================
CREATE TABLE IF NOT EXISTS forum_topic_tags (
    topic_id BIGINT NOT NULL REFERENCES forum_topics(id) ON DELETE CASCADE,
    tag_id   BIGINT NOT NULL REFERENCES forum_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (topic_id, tag_id)
);

-- ============================================================
-- 点赞
-- ============================================================
CREATE TABLE IF NOT EXISTS forum_likes (
    id          BIGSERIAL PRIMARY KEY,
    user_id     VARCHAR(64) NOT NULL,
    target_type VARCHAR(20) NOT NULL,
    target_id   BIGINT NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, target_type, target_id)
);

-- ============================================================
-- 收藏
-- ============================================================
CREATE TABLE IF NOT EXISTS forum_bookmarks (
    id          BIGSERIAL PRIMARY KEY,
    user_id     VARCHAR(64) NOT NULL,
    topic_id    BIGINT NOT NULL REFERENCES forum_topics(id) ON DELETE CASCADE,
    created_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, topic_id)
);

-- ============================================================
-- Q&A 问题
-- ============================================================
CREATE TABLE IF NOT EXISTS qa_questions (
    id              BIGSERIAL PRIMARY KEY,
    user_id         VARCHAR(64) NOT NULL,
    title           VARCHAR(500) NOT NULL,
    content         TEXT NOT NULL,
    content_html    TEXT NOT NULL,
    view_count      INT DEFAULT 0,
    answer_count    INT DEFAULT 0,
    vote_score      INT DEFAULT 0,
    accepted_answer_id BIGINT,
    is_solved       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_questions_vote ON qa_questions(vote_score DESC);
CREATE INDEX idx_questions_created ON qa_questions(created_at DESC);

-- ============================================================
-- Q&A 答案
-- ============================================================
CREATE TABLE IF NOT EXISTS qa_answers (
    id              BIGSERIAL PRIMARY KEY,
    question_id     BIGINT NOT NULL REFERENCES qa_questions(id) ON DELETE CASCADE,
    user_id         VARCHAR(64) NOT NULL,
    content         TEXT NOT NULL,
    content_html    TEXT NOT NULL,
    vote_score      INT DEFAULT 0,
    is_accepted     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_answers_question ON qa_answers(question_id, vote_score DESC);

-- ============================================================
-- Q&A 投票
-- ============================================================
CREATE TABLE IF NOT EXISTS qa_votes (
    id              BIGSERIAL PRIMARY KEY,
    user_id         VARCHAR(64) NOT NULL,
    target_type     VARCHAR(20) NOT NULL,
    target_id       BIGINT NOT NULL,
    vote_type       VARCHAR(10) NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, target_type, target_id)
);

-- ============================================================
-- 活动
-- ============================================================
CREATE TABLE IF NOT EXISTS events (
    id              BIGSERIAL PRIMARY KEY,
    title           VARCHAR(500) NOT NULL,
    slug            VARCHAR(200) NOT NULL UNIQUE,
    type            VARCHAR(30) NOT NULL,
    description     TEXT,
    content_html    TEXT,
    cover_url       VARCHAR(512),
    location        VARCHAR(500),
    start_time      TIMESTAMP NOT NULL,
    end_time        TIMESTAMP NOT NULL,
    timezone        VARCHAR(50) DEFAULT 'Asia/Shanghai',
    max_attendees   INT,
    current_attendees INT DEFAULT 0,
    status          VARCHAR(20) DEFAULT 'DRAFT',
    is_featured     BOOLEAN DEFAULT FALSE,
    created_by      VARCHAR(64) NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_events_status ON events(status, start_time);
CREATE INDEX idx_events_type ON events(type, start_time);

-- ============================================================
-- 活动报名
-- ============================================================
CREATE TABLE IF NOT EXISTS event_registrations (
    id          BIGSERIAL PRIMARY KEY,
    event_id    BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id     VARCHAR(64) NOT NULL,
    name        VARCHAR(100),
    company     VARCHAR(200),
    title       VARCHAR(200),
    email       VARCHAR(200),
    checked_in  BOOLEAN DEFAULT FALSE,
    checked_in_at TIMESTAMP,
    created_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, user_id)
);

-- ============================================================
-- 活动议程
-- ============================================================
CREATE TABLE IF NOT EXISTS event_agenda_items (
    id          BIGSERIAL PRIMARY KEY,
    event_id    BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    title       VARCHAR(500) NOT NULL,
    description TEXT,
    speaker     VARCHAR(200),
    speaker_title VARCHAR(200),
    start_time  TIMESTAMP NOT NULL,
    end_time    TIMESTAMP NOT NULL,
    location    VARCHAR(200),
    sort_order  INT DEFAULT 0
);

-- ============================================================
-- 活动资料
-- ============================================================
CREATE TABLE IF NOT EXISTS event_materials (
    id          BIGSERIAL PRIMARY KEY,
    event_id    BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    title       VARCHAR(500) NOT NULL,
    file_url    VARCHAR(512) NOT NULL,
    file_type   VARCHAR(50),
    file_size   BIGINT,
    download_count INT DEFAULT 0,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- 学院课程
-- ============================================================
CREATE TABLE IF NOT EXISTS academy_courses (
    id              BIGSERIAL PRIMARY KEY,
    title           VARCHAR(500) NOT NULL,
    slug            VARCHAR(200) NOT NULL UNIQUE,
    description     TEXT,
    cover_url       VARCHAR(512),
    level           VARCHAR(20) NOT NULL,
    category        VARCHAR(50),
    lesson_count    INT DEFAULT 0,
    enrolled_count  INT DEFAULT 0,
    duration_minutes INT DEFAULT 0,
    is_published    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_courses_level ON academy_courses(level);
CREATE INDEX idx_courses_category ON academy_courses(category);

-- ============================================================
-- 学院课时
-- ============================================================
CREATE TABLE IF NOT EXISTS academy_lessons (
    id          BIGSERIAL PRIMARY KEY,
    course_id   BIGINT NOT NULL REFERENCES academy_courses(id) ON DELETE CASCADE,
    title       VARCHAR(500) NOT NULL,
    content     TEXT,
    content_html TEXT,
    video_url   VARCHAR(512),
    duration_minutes INT DEFAULT 0,
    sort_order  INT DEFAULT 0,
    is_free     BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_lessons_course ON academy_lessons(course_id, sort_order);

-- ============================================================
-- 学院报名
-- ============================================================
CREATE TABLE IF NOT EXISTS academy_enrollments (
    id              BIGSERIAL PRIMARY KEY,
    user_id         VARCHAR(64) NOT NULL,
    course_id       BIGINT NOT NULL REFERENCES academy_courses(id) ON DELETE CASCADE,
    progress_pct    INT DEFAULT 0,
    completed_at    TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, course_id)
);

-- ============================================================
-- 认证
-- ============================================================
CREATE TABLE IF NOT EXISTS academy_certifications (
    id              BIGSERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    slug            VARCHAR(100) NOT NULL UNIQUE,
    level           VARCHAR(20) NOT NULL,
    description     TEXT,
    exam_duration   INT DEFAULT 60,
    pass_score      INT DEFAULT 70,
    question_count  INT DEFAULT 50,
    validity_months INT DEFAULT 24,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- 用户认证
-- ============================================================
CREATE TABLE IF NOT EXISTS academy_user_certifications (
    id              BIGSERIAL PRIMARY KEY,
    user_id         VARCHAR(64) NOT NULL,
    certification_id BIGINT NOT NULL REFERENCES academy_certifications(id),
    score           INT NOT NULL,
    passed          BOOLEAN NOT NULL,
    certificate_url VARCHAR(512),
    issued_at       TIMESTAMP DEFAULT NOW(),
    expires_at      TIMESTAMP,
    UNIQUE(user_id, certification_id)
);

-- ============================================================
-- 博客
-- ============================================================
CREATE TABLE IF NOT EXISTS content_blogs (
    id          BIGSERIAL PRIMARY KEY,
    title       VARCHAR(500) NOT NULL,
    slug        VARCHAR(200) NOT NULL UNIQUE,
    summary     TEXT,
    content     TEXT NOT NULL,
    content_html TEXT NOT NULL,
    cover_url   VARCHAR(512),
    author_id   VARCHAR(64) NOT NULL,
    tags        VARCHAR(50)[],
    is_published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMP,
    view_count  INT DEFAULT 0,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_blogs_published ON content_blogs(published_at DESC) WHERE is_published = TRUE;

-- ============================================================
-- 案例展示
-- ============================================================
CREATE TABLE IF NOT EXISTS content_showcases (
    id              BIGSERIAL PRIMARY KEY,
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    content_html    TEXT,
    cover_url       VARCHAR(512),
    video_url       VARCHAR(512),
    project_url     VARCHAR(512),
    author_id       VARCHAR(64) NOT NULL,
    category        VARCHAR(50),
    tags            VARCHAR(50)[],
    is_featured     BOOLEAN DEFAULT FALSE,
    like_count      INT DEFAULT 0,
    view_count      INT DEFAULT 0,
    status          VARCHAR(20) DEFAULT 'PENDING',
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_showcases_featured ON content_showcases(is_featured, created_at DESC);

-- ============================================================
-- TSC 成员
-- ============================================================
CREATE TABLE IF NOT EXISTS governance_tsc_members (
    id          BIGSERIAL PRIMARY KEY,
    user_id     VARCHAR(64) NOT NULL UNIQUE,
    role        VARCHAR(50),
    term_start  DATE NOT NULL,
    term_end    DATE NOT NULL,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- SIG 专项兴趣小组
-- ============================================================
CREATE TABLE IF NOT EXISTS governance_sigs (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL UNIQUE,
    slug        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    chair_id    VARCHAR(64),
    member_count INT DEFAULT 0,
    meeting_schedule VARCHAR(200),
    created_at  TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- RFC
-- ============================================================
CREATE TABLE IF NOT EXISTS governance_rfcs (
    id          BIGSERIAL PRIMARY KEY,
    title       VARCHAR(500) NOT NULL,
    number      VARCHAR(20) NOT NULL UNIQUE,
    status      VARCHAR(20) DEFAULT 'DRAFT',
    content     TEXT NOT NULL,
    content_html TEXT NOT NULL,
    author_id   VARCHAR(64) NOT NULL,
    sig_id      BIGINT REFERENCES governance_sigs(id),
    vote_yes    INT DEFAULT 0,
    vote_no     INT DEFAULT 0,
    vote_abstain INT DEFAULT 0,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- RFC 投票记录
-- ============================================================
CREATE TABLE IF NOT EXISTS governance_rfc_votes (
    id          BIGSERIAL PRIMARY KEY,
    rfc_id      BIGINT NOT NULL REFERENCES governance_rfcs(id) ON DELETE CASCADE,
    user_id     VARCHAR(64) NOT NULL,
    vote        VARCHAR(10) NOT NULL,
    comment     TEXT,
    created_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE(rfc_id, user_id)
);
