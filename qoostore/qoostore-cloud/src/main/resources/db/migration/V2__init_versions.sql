-- V2: Skill Versions & Submissions
CREATE TABLE IF NOT EXISTS skill_versions (
    id BIGSERIAL PRIMARY KEY,
    skill_id BIGINT NOT NULL REFERENCES skills(id),
    version VARCHAR(32) NOT NULL,
    changelog TEXT,
    package_url VARCHAR(1024),
    package_size BIGINT,
    package_hash VARCHAR(128),
    manifest_json JSONB,
    min_qos_version VARCHAR(16),
    privacy_label JSONB,
    permissions TEXT[],
    status VARCHAR(16) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(skill_id, version)
);

CREATE TABLE IF NOT EXISTS submissions (
    id BIGSERIAL PRIMARY KEY,
    version_id BIGINT NOT NULL REFERENCES skill_versions(id),
    type VARCHAR(16) DEFAULT 'new',
    status VARCHAR(16) DEFAULT 'pending',
    auto_scan_id VARCHAR(64),
    scan_result JSONB,
    reviewer_id UUID,
    reject_reason TEXT,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_skill_versions_skill_id ON skill_versions(skill_id);
CREATE INDEX idx_skill_versions_status ON skill_versions(status);
CREATE INDEX idx_submissions_status ON submissions(status);
