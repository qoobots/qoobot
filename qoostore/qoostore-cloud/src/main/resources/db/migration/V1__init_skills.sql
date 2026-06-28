-- V1: Developers & Skills
CREATE TABLE IF NOT EXISTS developers (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE,
    username VARCHAR(64) NOT NULL UNIQUE,
    display_name VARCHAR(128),
    email VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    website VARCHAR(512),
    verified BOOLEAN DEFAULT FALSE,
    tax_id VARCHAR(64),
    payout_method VARCHAR(32),
    payout_account VARCHAR(512),
    status VARCHAR(16) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    slug VARCHAR(64) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(255),
    parent_id BIGINT REFERENCES categories(id),
    sort_order INTEGER DEFAULT 0,
    status VARCHAR(16) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS skills (
    id BIGSERIAL PRIMARY KEY,
    skill_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    developer_id BIGINT NOT NULL REFERENCES developers(id),
    category_id BIGINT REFERENCES categories(id),
    tagline VARCHAR(255),
    description TEXT,
    icon_url VARCHAR(1024),
    privacy_level VARCHAR(16) DEFAULT 'public',
    status VARCHAR(16) DEFAULT 'draft',
    pricing_model VARCHAR(32) DEFAULT 'free',
    price DECIMAL(10,2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'USD',
    trial_days INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP
);

CREATE INDEX idx_skills_skill_id ON skills(skill_id);
CREATE INDEX idx_skills_developer_id ON skills(developer_id);
CREATE INDEX idx_skills_category_id ON skills(category_id);
CREATE INDEX idx_skills_status ON skills(status);

-- Seed default categories
INSERT INTO categories (name, slug, description, sort_order) VALUES
    ('家务', 'home', '清洁、整理、烹饪辅助等家务技能', 1),
    ('工业', 'industrial', '装配、质检、搬运、焊接等工业技能', 2),
    ('医疗', 'medical', '手术辅助、康复训练、药品配送', 3),
    ('零售', 'retail', '导购、理货、盘点', 4),
    ('农业', 'agriculture', '采摘、巡检、喷洒', 5),
    ('娱乐', 'entertainment', '下棋、舞蹈、陪伴', 6),
    ('教育', 'education', '教学辅助、实验演示、语言学习', 7)
ON CONFLICT DO NOTHING;
