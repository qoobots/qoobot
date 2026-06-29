-- ============================================================================
-- QooCompliance Database Schema - Initial Migration
-- PostgreSQL DDL for compliance management
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. compliance_regulation - 法规条目
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compliance_regulation (
    id              BIGSERIAL       PRIMARY KEY,
    regulation_id   VARCHAR(64)     NOT NULL,
    title           VARCHAR(255)    NOT NULL,
    short_name      VARCHAR(128),
    category        VARCHAR(64),
    market          VARCHAR(8),
    authority       VARCHAR(128),
    summary         TEXT,
    status          VARCHAR(32),
    effective_date  DATE,
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_regulation_regulation_id ON compliance_regulation (regulation_id);
CREATE INDEX IF NOT EXISTS idx_regulation_category       ON compliance_regulation (category);
CREATE INDEX IF NOT EXISTS idx_regulation_market         ON compliance_regulation (market);
CREATE INDEX IF NOT EXISTS idx_regulation_status         ON compliance_regulation (status);

-- ---------------------------------------------------------------------------
-- 2. compliance_checklist - 合规检查清单
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compliance_checklist (
    id              BIGSERIAL       PRIMARY KEY,
    checklist_id    VARCHAR(64)     NOT NULL,
    project_id      VARCHAR(64)     NOT NULL,
    project_name    VARCHAR(255),
    market          VARCHAR(8),
    status          VARCHAR(32),
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_checklist_checklist_id ON compliance_checklist (checklist_id);
CREATE INDEX IF NOT EXISTS idx_checklist_project_id          ON compliance_checklist (project_id);
CREATE INDEX IF NOT EXISTS idx_checklist_market              ON compliance_checklist (market);
CREATE INDEX IF NOT EXISTS idx_checklist_status              ON compliance_checklist (status);

-- ---------------------------------------------------------------------------
-- 3. compliance_item - 合规检查项
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compliance_item (
    id              BIGSERIAL       PRIMARY KEY,
    item_id         VARCHAR(64)     NOT NULL,
    checklist_id    VARCHAR(64)     NOT NULL,
    project_id      VARCHAR(64),
    category        VARCHAR(64),
    title           VARCHAR(255),
    description     TEXT,
    priority        VARCHAR(8),
    status          VARCHAR(32),
    evidence        TEXT,
    notes           TEXT,
    reviewer        VARCHAR(128),
    reviewed_at     TIMESTAMP,
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_item_item_id     ON compliance_item (item_id);
CREATE INDEX IF NOT EXISTS idx_item_checklist_id       ON compliance_item (checklist_id);
CREATE INDEX IF NOT EXISTS idx_item_project_id         ON compliance_item (project_id);
CREATE INDEX IF NOT EXISTS idx_item_category           ON compliance_item (category);
CREATE INDEX IF NOT EXISTS idx_item_status             ON compliance_item (status);
CREATE INDEX IF NOT EXISTS idx_item_priority           ON compliance_item (priority);

-- ---------------------------------------------------------------------------
-- 4. certification_progress - 认证进度
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS certification_progress (
    id              BIGSERIAL       PRIMARY KEY,
    product_id      VARCHAR(64)     NOT NULL,
    market          VARCHAR(8),
    cert_type       VARCHAR(64),
    cert_number     VARCHAR(128),
    status          VARCHAR(32),
    applied_at      DATE,
    approved_at     DATE,
    expires_at      DATE,
    lab_name        VARCHAR(128),
    notes           TEXT,
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cert_progress_product_id  ON certification_progress (product_id);
CREATE INDEX IF NOT EXISTS idx_cert_progress_market      ON certification_progress (market);
CREATE INDEX IF NOT EXISTS idx_cert_progress_status      ON certification_progress (status);
CREATE INDEX IF NOT EXISTS idx_cert_progress_cert_number ON certification_progress (cert_number);

-- ---------------------------------------------------------------------------
-- 5. compliance_review - 合规审查记录
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compliance_review (
    id              BIGSERIAL       PRIMARY KEY,
    product_id      VARCHAR(64)     NOT NULL,
    review_type     VARCHAR(64),
    status          VARCHAR(32),
    findings        TEXT,
    reviewer_id     VARCHAR(64),
    reviewer_name   VARCHAR(128),
    reviewed_at     TIMESTAMP,
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_review_product_id  ON compliance_review (product_id);
CREATE INDEX IF NOT EXISTS idx_review_review_type ON compliance_review (review_type);
CREATE INDEX IF NOT EXISTS idx_review_status      ON compliance_review (status);
CREATE INDEX IF NOT EXISTS idx_review_reviewer_id ON compliance_review (reviewer_id);

-- ---------------------------------------------------------------------------
-- 6. regulation_change - 法规变更记录
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS regulation_change (
    id                  BIGSERIAL       PRIMARY KEY,
    regulation_id       VARCHAR(64)     NOT NULL,
    change_type         VARCHAR(32),
    title               VARCHAR(255),
    description         TEXT,
    effective_date      DATE,
    impact_level        VARCHAR(32),
    affected_products   TEXT,
    notified            BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reg_change_regulation_id  ON regulation_change (regulation_id);
CREATE INDEX IF NOT EXISTS idx_reg_change_change_type    ON regulation_change (change_type);
CREATE INDEX IF NOT EXISTS idx_reg_change_impact_level   ON regulation_change (impact_level);
CREATE INDEX IF NOT EXISTS idx_reg_change_effective_date ON regulation_change (effective_date);

-- ---------------------------------------------------------------------------
-- 7. audit_record - 审计记录
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_record (
    id              BIGSERIAL       PRIMARY KEY,
    action          VARCHAR(64),
    product_id      VARCHAR(64),
    market          VARCHAR(8),
    user_id         VARCHAR(64),
    details         TEXT,
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_product_id ON audit_record (product_id);
CREATE INDEX IF NOT EXISTS idx_audit_action     ON audit_record (action);
CREATE INDEX IF NOT EXISTS idx_audit_user_id    ON audit_record (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_record (created_at);
