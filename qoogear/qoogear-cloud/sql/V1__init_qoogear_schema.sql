-- V1__init_qoogear_schema.sql
-- QooGear Made for QooBot Certification Platform - Initial Schema

-- 1. Developers
CREATE TABLE IF NOT EXISTS developers (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL UNIQUE,
    company_name    VARCHAR(200) NOT NULL,
    contact_name    VARCHAR(100) NOT NULL,
    contact_email   VARCHAR(255) NOT NULL,
    contact_phone   VARCHAR(50),
    website         VARCHAR(500),
    country         VARCHAR(100),
    business_license VARCHAR(500),
    verified_at     TIMESTAMPTZ,
    verification_status VARCHAR(20) DEFAULT 'pending',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_developers_user_id ON developers(user_id);
CREATE INDEX idx_developers_verified ON developers(verification_status);

-- 2. Certification Applications
CREATE TABLE IF NOT EXISTS cert_applications (
    id              BIGSERIAL PRIMARY KEY,
    developer_id    BIGINT NOT NULL REFERENCES developers(id),
    product_name    VARCHAR(200) NOT NULL,
    product_category VARCHAR(50) NOT NULL,
    product_model   VARCHAR(100) NOT NULL,
    product_description TEXT,
    cert_level      VARCHAR(20) NOT NULL,
    standard_ids    BIGINT[] NOT NULL,
    mechanical_spec_url  VARCHAR(500),
    electrical_spec_url  VARCHAR(500),
    communication_protocol_url VARCHAR(500),
    firmware_source_url   VARCHAR(500),
    test_samples_count    INT DEFAULT 2,
    status          VARCHAR(30) NOT NULL DEFAULT 'draft',
    submitted_at    TIMESTAMPTZ,
    reviewed_by     BIGINT,
    review_comment  TEXT,
    reviewed_at     TIMESTAMPTZ,
    assigned_lab_id BIGINT,
    assigned_at     TIMESTAMPTZ,
    approved_at     TIMESTAMPTZ,
    rejection_reason TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cert_app_developer ON cert_applications(developer_id);
CREATE INDEX idx_cert_app_status ON cert_applications(status);
CREATE INDEX idx_cert_app_category ON cert_applications(product_category);

-- 3. Certificates
CREATE TABLE IF NOT EXISTS certificates (
    id              BIGSERIAL PRIMARY KEY,
    application_id  BIGINT NOT NULL UNIQUE REFERENCES cert_applications(id),
    cert_number     VARCHAR(50) NOT NULL UNIQUE,
    cert_level      VARCHAR(20) NOT NULL,
    developer_id    BIGINT NOT NULL REFERENCES developers(id),
    product_name    VARCHAR(200) NOT NULL,
    product_model   VARCHAR(100) NOT NULL,
    product_category VARCHAR(50) NOT NULL,
    issued_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    revoke_reason   TEXT,
    public_key      TEXT,
    cert_doc_url    VARCHAR(500),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_certificates_number ON certificates(cert_number);
CREATE INDEX idx_certificates_developer ON certificates(developer_id);
CREATE INDEX idx_certificates_expires ON certificates(expires_at);

-- 4. Authorization Chips
CREATE TABLE IF NOT EXISTS auth_chips (
    id              BIGSERIAL PRIMARY KEY,
    certificate_id  BIGINT NOT NULL REFERENCES certificates(id),
    chip_id         VARCHAR(100) NOT NULL UNIQUE,
    chip_type       VARCHAR(50) NOT NULL,
    batch_number    VARCHAR(100) NOT NULL,
    burned_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_auth_chips_cert ON auth_chips(certificate_id);
CREATE INDEX idx_auth_chips_batch ON auth_chips(batch_number);

-- 5. Standard Categories
CREATE TABLE IF NOT EXISTS standard_categories (
    id              BIGSERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    slug            VARCHAR(100) NOT NULL UNIQUE,
    parent_id       BIGINT REFERENCES standard_categories(id),
    description     TEXT,
    icon            VARCHAR(50),
    sort_order      INT DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_std_categories_parent ON standard_categories(parent_id);

-- 6. Standard Specs
CREATE TABLE IF NOT EXISTS standard_specs (
    id              BIGSERIAL PRIMARY KEY,
    category_id     BIGINT NOT NULL REFERENCES standard_categories(id),
    title           VARCHAR(300) NOT NULL,
    spec_number     VARCHAR(50) NOT NULL,
    version         VARCHAR(20) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'draft',
    description     TEXT,
    spec_doc_url    VARCHAR(500) NOT NULL,
    changelog       TEXT,
    published_at    TIMESTAMPTZ,
    deprecated_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(spec_number, version)
);

CREATE INDEX idx_standard_specs_category ON standard_specs(category_id);
CREATE INDEX idx_standard_specs_status ON standard_specs(status);

-- 7. Compatibility Matrix
CREATE TABLE IF NOT EXISTS compatibility_matrix (
    id              BIGSERIAL PRIMARY KEY,
    spec_id_a       BIGINT NOT NULL REFERENCES standard_specs(id),
    spec_version_a  VARCHAR(20) NOT NULL,
    spec_id_b       BIGINT NOT NULL REFERENCES standard_specs(id),
    spec_version_b  VARCHAR(20) NOT NULL,
    compatibility   VARCHAR(20) NOT NULL,
    condition_desc  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(spec_id_a, spec_version_a, spec_id_b, spec_version_b)
);

-- 8. Test Checklist
CREATE TABLE IF NOT EXISTS test_checklist (
    id              BIGSERIAL PRIMARY KEY,
    standard_id     BIGINT NOT NULL REFERENCES standard_specs(id),
    test_item       VARCHAR(200) NOT NULL,
    test_method     TEXT,
    criteria        TEXT NOT NULL,
    required        BOOLEAN NOT NULL DEFAULT true,
    sort_order      INT DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_test_checklist_standard ON test_checklist(standard_id);

-- 9. Test Reports
CREATE TABLE IF NOT EXISTS test_reports (
    id              BIGSERIAL PRIMARY KEY,
    application_id  BIGINT NOT NULL REFERENCES cert_applications(id),
    laboratory_id   BIGINT NOT NULL,
    test_engineer   VARCHAR(100),
    overall_result  VARCHAR(20) NOT NULL,
    summary         TEXT,
    test_data_json  JSONB,
    attachments     VARCHAR(500)[],
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_test_reports_app ON test_reports(application_id);
CREATE INDEX idx_test_reports_lab ON test_reports(laboratory_id);

-- 10. Laboratories
CREATE TABLE IF NOT EXISTS laboratories (
    id              BIGSERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    lab_code        VARCHAR(50) NOT NULL UNIQUE,
    country         VARCHAR(100) NOT NULL,
    city            VARCHAR(100),
    address         TEXT NOT NULL,
    contact_name    VARCHAR(100) NOT NULL,
    contact_email   VARCHAR(255) NOT NULL,
    contact_phone   VARCHAR(50),
    accreditation   VARCHAR(200),
    scope           VARCHAR(100)[],
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_laboratories_scope ON laboratories USING GIN(scope);
CREATE INDEX idx_laboratories_status ON laboratories(status);

-- 11. Lab Equipment
CREATE TABLE IF NOT EXISTS lab_equipment (
    id              BIGSERIAL PRIMARY KEY,
    laboratory_id   BIGINT NOT NULL REFERENCES laboratories(id),
    name            VARCHAR(200) NOT NULL,
    model           VARCHAR(100),
    serial_number   VARCHAR(100) NOT NULL,
    equipment_type  VARCHAR(50) NOT NULL,
    calibrated_at   TIMESTAMPTZ,
    next_calibration_due TIMESTAMPTZ,
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_lab_equipment_lab ON lab_equipment(laboratory_id);
CREATE INDEX idx_lab_equipment_cal ON lab_equipment(next_calibration_due);

-- 12. Security Audits
CREATE TABLE IF NOT EXISTS security_audits (
    id              BIGSERIAL PRIMARY KEY,
    application_id  BIGINT NOT NULL REFERENCES cert_applications(id),
    risk_level      VARCHAR(20) NOT NULL,
    fmea_json       JSONB,
    auditor_id      BIGINT NOT NULL,
    findings        TEXT,
    recommendation  TEXT,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_security_audits_app ON security_audits(application_id);
CREATE INDEX idx_security_audits_risk ON security_audits(risk_level);

-- 13. Reference Designs
CREATE TABLE IF NOT EXISTS reference_designs (
    id              BIGSERIAL PRIMARY KEY,
    title           VARCHAR(300) NOT NULL,
    category        VARCHAR(50) NOT NULL,
    description     TEXT,
    files           JSONB NOT NULL,
    download_count  BIGINT DEFAULT 0,
    published_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ref_designs_category ON reference_designs(category);

-- 14. SDK Releases
CREATE TABLE IF NOT EXISTS sdk_releases (
    id              BIGSERIAL PRIMARY KEY,
    platform        VARCHAR(20) NOT NULL,
    version         VARCHAR(20) NOT NULL,
    download_url    VARCHAR(500) NOT NULL,
    file_size       BIGINT,
    checksum_sha256 VARCHAR(64),
    release_notes   TEXT,
    is_latest       BOOLEAN DEFAULT false,
    released_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(platform, version)
);

CREATE INDEX idx_sdk_releases_platform ON sdk_releases(platform);

-- 15. Test Kits
CREATE TABLE IF NOT EXISTS test_kits (
    id              BIGSERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    kit_type        VARCHAR(50) NOT NULL,
    price           DECIMAL(10,2),
    currency        VARCHAR(10) DEFAULT 'CNY',
    stock           INT DEFAULT 0,
    compatible_standards BIGINT[],
    image_url       VARCHAR(500),
    is_available    BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 16. Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    actor           VARCHAR(100) NOT NULL,
    actor_type      VARCHAR(20) NOT NULL,
    action          VARCHAR(50) NOT NULL,
    resource_type   VARCHAR(50) NOT NULL,
    resource_id     BIGINT,
    details_json    JSONB,
    ip_address      VARCHAR(45),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_actor ON audit_logs(actor);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);

-- Seed Data: Standard Categories
INSERT INTO standard_categories (name, slug, description, sort_order) VALUES
    ('机械接口', 'mechanical', '法兰尺寸/螺栓孔位/定位销/负载等级规范', 1),
    ('电气接口', 'electrical', '供电规格/信号引脚/连接器型号规范', 2),
    ('通信协议', 'communication', 'CAN/EtherCAT/RS-485/I2C/SPI 规范', 3),
    ('传感器数据', 'sensor-data', '视觉/深度/触觉/环境数据格式', 4),
    ('快换系统', 'quick-change', '工具快换机械/电气/识别接口', 5),
    ('安全互锁', 'safety-interlock', '急停联动/脱落检测/紧急释放', 6),
    ('电源配件', 'power-accessories', '充电触点/无线充电/电池通信', 7)
ON CONFLICT (slug) DO NOTHING;

-- Seed Data: SDK Releases
INSERT INTO sdk_releases (platform, version, download_url, is_latest, released_at) VALUES
    ('python', '0.1.0', 'https://releases.qoobot.io/qoogear/sdk/python/qoogear-sdk-0.1.0.tar.gz', true, NOW()),
    ('cpp', '0.1.0', 'https://releases.qoobot.io/qoogear/sdk/cpp/qoogear-sdk-0.1.0.tar.gz', true, NOW())
ON CONFLICT (platform, version) DO NOTHING;
