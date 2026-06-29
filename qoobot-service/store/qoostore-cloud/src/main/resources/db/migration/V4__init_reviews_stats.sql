-- V4: Reviews & Stats
CREATE TABLE IF NOT EXISTS reviews (
    id BIGSERIAL PRIMARY KEY,
    skill_id BIGINT NOT NULL REFERENCES skills(id),
    user_id UUID NOT NULL,
    order_id BIGINT REFERENCES orders(id),
    rating SMALLINT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(255),
    content TEXT,
    helpful_count INTEGER DEFAULT 0,
    status VARCHAR(16) DEFAULT 'published',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(skill_id, user_id)
);

CREATE TABLE IF NOT EXISTS skill_stats (
    id BIGSERIAL PRIMARY KEY,
    skill_id BIGINT NOT NULL REFERENCES skills(id),
    date DATE NOT NULL,
    downloads INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    revenue DECIMAL(12,2) DEFAULT 0.00,
    crash_count INTEGER DEFAULT 0,
    avg_rating DECIMAL(3,2),
    review_count INTEGER DEFAULT 0,
    UNIQUE(skill_id, date)
);

CREATE TABLE IF NOT EXISTS developer_revenue (
    id BIGSERIAL PRIMARY KEY,
    developer_id BIGINT NOT NULL REFERENCES developers(id),
    order_id BIGINT NOT NULL REFERENCES orders(id),
    skill_id BIGINT NOT NULL REFERENCES skills(id),
    gross_amount DECIMAL(10,2) NOT NULL,
    platform_fee DECIMAL(10,2) NOT NULL,
    developer_share DECIMAL(10,2) NOT NULL,
    share_rate DECIMAL(5,4) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS developer_payouts (
    id BIGSERIAL PRIMARY KEY,
    developer_id BIGINT NOT NULL REFERENCES developers(id),
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    status VARCHAR(16) DEFAULT 'pending',
    payout_method VARCHAR(32),
    transaction_id VARCHAR(255),
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS device_skills (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(128) NOT NULL,
    skill_id BIGINT NOT NULL REFERENCES skills(id),
    version_id BIGINT REFERENCES skill_versions(id),
    license_id BIGINT REFERENCES licenses(id),
    status VARCHAR(16) DEFAULT 'installing',
    installed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(device_id, skill_id)
);

CREATE INDEX idx_reviews_skill_id ON reviews(skill_id);
CREATE INDEX idx_skill_stats_skill_date ON skill_stats(skill_id, date);
CREATE INDEX idx_developer_revenue_dev ON developer_revenue(developer_id);
CREATE INDEX idx_developer_payouts_dev ON developer_payouts(developer_id);
CREATE INDEX idx_device_skills_device ON device_skills(device_id);
