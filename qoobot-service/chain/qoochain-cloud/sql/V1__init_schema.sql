-- V1: Initial schema for qoochain database
-- All tables for manufacturing, calibration, quality, traceability, logistics, and aftermarket

-- Products & BOM
CREATE TABLE IF NOT EXISTS product (
    id              BIGSERIAL PRIMARY KEY,
    model_code      VARCHAR(64)  NOT NULL UNIQUE,
    model_name      VARCHAR(128) NOT NULL,
    category        VARCHAR(32)  NOT NULL,
    status          VARCHAR(16)  NOT NULL DEFAULT 'DRAFT',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bom (
    id              BIGSERIAL PRIMARY KEY,
    product_id      BIGINT       NOT NULL REFERENCES product(id),
    version         VARCHAR(16)  NOT NULL,
    bom_type        VARCHAR(8)   NOT NULL,
    status          VARCHAR(16)  NOT NULL DEFAULT 'DRAFT',
    total_items     INT          NOT NULL DEFAULT 0,
    estimated_cost  NUMERIC(12,2),
    cost_currency   VARCHAR(3)   DEFAULT 'CNY',
    released_at     DATE,
    created_by      VARCHAR(64)  NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(product_id, version, bom_type)
);

CREATE TABLE IF NOT EXISTS material (
    id              BIGSERIAL PRIMARY KEY,
    material_code   VARCHAR(64)  NOT NULL UNIQUE,
    material_name   VARCHAR(128) NOT NULL,
    category        VARCHAR(32)  NOT NULL,
    specification   TEXT,
    manufacturer    VARCHAR(128),
    manufacturer_pn VARCHAR(64),
    lifecycle       VARCHAR(16)  NOT NULL DEFAULT 'ACTIVE',
    lead_time_days  INT,
    moq             INT,
    rohs_compliant  BOOLEAN      DEFAULT FALSE,
    reach_compliant BOOLEAN      DEFAULT FALSE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bom_item (
    id              BIGSERIAL PRIMARY KEY,
    bom_id          BIGINT       NOT NULL REFERENCES bom(id),
    parent_item_id  BIGINT       REFERENCES bom_item(id),
    item_code       VARCHAR(64)  NOT NULL,
    item_name       VARCHAR(128) NOT NULL,
    level           INT          NOT NULL DEFAULT 0,
    quantity        NUMERIC(10,3) NOT NULL DEFAULT 1,
    unit            VARCHAR(16)  NOT NULL DEFAULT 'PCS',
    material_id     BIGINT       REFERENCES material(id),
    is_critical     BOOLEAN      NOT NULL DEFAULT FALSE,
    sort_order      INT          NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bom_item_bom ON bom_item(bom_id);
CREATE INDEX IF NOT EXISTS idx_bom_item_parent ON bom_item(parent_item_id);

CREATE TABLE IF NOT EXISTS supplier (
    id              BIGSERIAL PRIMARY KEY,
    supplier_code   VARCHAR(64)  NOT NULL UNIQUE,
    supplier_name   VARCHAR(128) NOT NULL,
    category        VARCHAR(32)  NOT NULL,
    country         VARCHAR(64),
    rating          INT          NOT NULL DEFAULT 3,
    status          VARCHAR(16)  NOT NULL DEFAULT 'QUALIFIED',
    contact_name    VARCHAR(64),
    contact_email   VARCHAR(128),
    contact_phone   VARCHAR(32),
    audit_date      DATE,
    audit_report_url VARCHAR(512),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS material_supplier (
    id              BIGSERIAL PRIMARY KEY,
    material_id     BIGINT       NOT NULL REFERENCES material(id),
    supplier_id     BIGINT       NOT NULL REFERENCES supplier(id),
    supplier_pn     VARCHAR(64),
    unit_price      NUMERIC(10,2),
    currency        VARCHAR(3)   DEFAULT 'CNY',
    is_preferred    BOOLEAN      DEFAULT FALSE,
    qualification_status VARCHAR(16) DEFAULT 'QUALIFIED',
    qualified_at    DATE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(material_id, supplier_id)
);

CREATE TABLE IF NOT EXISTS material_alternative (
    id              BIGSERIAL PRIMARY KEY,
    material_id     BIGINT       NOT NULL REFERENCES material(id),
    alternative_id  BIGINT       NOT NULL REFERENCES material(id),
    compatibility   VARCHAR(16)  NOT NULL,
    verified        BOOLEAN      DEFAULT FALSE,
    verified_at     TIMESTAMPTZ,
    notes           TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(material_id, alternative_id),
    CHECK(material_id <> alternative_id)
);

CREATE TABLE IF NOT EXISTS cost_record (
    id              BIGSERIAL PRIMARY KEY,
    material_id     BIGINT       NOT NULL REFERENCES material(id),
    supplier_id     BIGINT       NOT NULL REFERENCES supplier(id),
    unit_price      NUMERIC(10,2) NOT NULL,
    currency        VARCHAR(3)   DEFAULT 'CNY',
    effective_from  DATE         NOT NULL,
    effective_to    DATE,
    change_reason   VARCHAR(64),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_cost_material ON cost_record(material_id);

-- Production Lines
CREATE TABLE IF NOT EXISTS production_line (
    id              BIGSERIAL PRIMARY KEY,
    line_code       VARCHAR(64)  NOT NULL UNIQUE,
    line_name       VARCHAR(128) NOT NULL,
    location        VARCHAR(128),
    product_model   VARCHAR(64)  NOT NULL,
    status          VARCHAR(16)  NOT NULL DEFAULT 'ACTIVE',
    takt_time_min   INT,
    daily_capacity  INT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS station (
    id              BIGSERIAL PRIMARY KEY,
    line_id         BIGINT       NOT NULL REFERENCES production_line(id),
    station_code    VARCHAR(64)  NOT NULL,
    station_name    VARCHAR(128) NOT NULL,
    sequence        INT          NOT NULL,
    cycle_time_min  INT          NOT NULL,
    tools_required  TEXT,
    poka_yoke_rules TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(line_id, station_code)
);

CREATE TABLE IF NOT EXISTS sop_step (
    id              BIGSERIAL PRIMARY KEY,
    station_id      BIGINT       NOT NULL REFERENCES station(id),
    step_number     INT          NOT NULL,
    description     TEXT         NOT NULL,
    duration_min    INT          NOT NULL,
    tools           VARCHAR(256),
    torque_spec     NUMERIC(8,2),
    inspection_point BOOLEAN     DEFAULT FALSE,
    image_url       VARCHAR(512),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(station_id, step_number)
);

CREATE TABLE IF NOT EXISTS dfm_check (
    id              BIGSERIAL PRIMARY KEY,
    product_id      BIGINT       NOT NULL,
    checklist_item  VARCHAR(256) NOT NULL,
    category        VARCHAR(32)  NOT NULL,
    status          VARCHAR(16)  NOT NULL DEFAULT 'OPEN',
    severity        VARCHAR(8)   DEFAULT 'MEDIUM',
    assignee        VARCHAR(64),
    resolution      TEXT,
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Robots & Calibration
CREATE TABLE IF NOT EXISTS robot (
    id              BIGSERIAL PRIMARY KEY,
    serial_number   VARCHAR(64)  NOT NULL UNIQUE,
    product_id      BIGINT       NOT NULL,
    hardware_version VARCHAR(16) NOT NULL,
    firmware_version VARCHAR(16),
    production_line_id BIGINT,
    status          VARCHAR(16)  NOT NULL DEFAULT 'MANUFACTURING',
    manufactured_at DATE,
    shipped_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS calibration_session (
    id              BIGSERIAL PRIMARY KEY,
    robot_id        BIGINT       NOT NULL REFERENCES robot(id),
    session_version VARCHAR(32)  NOT NULL,
    calib_type      VARCHAR(16)  NOT NULL,
    operator_id     VARCHAR(64)  NOT NULL,
    status          VARCHAR(16)  NOT NULL DEFAULT 'IN_PROGRESS',
    started_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    report_url      VARCHAR(512),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS calibration_result (
    id              BIGSERIAL PRIMARY KEY,
    session_id      BIGINT       NOT NULL REFERENCES calibration_session(id),
    sensor_type     VARCHAR(32)  NOT NULL,
    parameter_name  VARCHAR(64)  NOT NULL,
    parameter_value NUMERIC(16,8) NOT NULL,
    unit            VARCHAR(16),
    accuracy_metric VARCHAR(64),
    accuracy_value  NUMERIC(16,8),
    accuracy_unit   VARCHAR(16),
    spec_lower      NUMERIC(16,8),
    spec_upper      NUMERIC(16,8),
    passed          BOOLEAN      NOT NULL,
    raw_data_url    VARCHAR(512),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_calib_session ON calibration_result(session_id);

-- Quality
CREATE TABLE IF NOT EXISTS inspection_record (
    id              BIGSERIAL PRIMARY KEY,
    robot_id        BIGINT       REFERENCES robot(id),
    material_id     BIGINT       REFERENCES material(id),
    inspection_type VARCHAR(8)   NOT NULL,
    station_code    VARCHAR(64),
    inspector_id    VARCHAR(64)  NOT NULL,
    lot_number      VARCHAR(64),
    sample_size     INT,
    defect_count    INT          DEFAULT 0,
    overall_result  VARCHAR(10)  NOT NULL DEFAULT 'PENDING',
    notes           TEXT,
    inspected_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_insp_robot ON inspection_record(robot_id);
CREATE INDEX IF NOT EXISTS idx_insp_type_date ON inspection_record(inspection_type, inspected_at);

CREATE TABLE IF NOT EXISTS inspection_measurement (
    id              BIGSERIAL PRIMARY KEY,
    inspection_id   BIGINT       NOT NULL REFERENCES inspection_record(id),
    measurement_name VARCHAR(64) NOT NULL,
    value           NUMERIC(12,4) NOT NULL,
    unit            VARCHAR(16),
    spec_lower      NUMERIC(12,4),
    spec_upper      NUMERIC(12,4),
    result          VARCHAR(8)   NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_meas_inspection ON inspection_measurement(inspection_id);

CREATE TABLE IF NOT EXISTS burn_in_test (
    id              BIGSERIAL PRIMARY KEY,
    robot_id        BIGINT       NOT NULL REFERENCES robot(id),
    duration_hours  INT          NOT NULL,
    started_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    status          VARCHAR(16)  NOT NULL DEFAULT 'RUNNING',
    failure_reason  TEXT,
    log_url         VARCHAR(512),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS spc_statistics (
    id              BIGSERIAL PRIMARY KEY,
    measurement_name VARCHAR(64) NOT NULL,
    station_code    VARCHAR(64),
    period_start    TIMESTAMPTZ  NOT NULL,
    period_end      TIMESTAMPTZ  NOT NULL,
    sample_count    INT          NOT NULL,
    mean_value      NUMERIC(12,4),
    std_dev         NUMERIC(12,4),
    cp              NUMERIC(8,4),
    cpk             NUMERIC(8,4),
    ucl             NUMERIC(12,4),
    lcl             NUMERIC(12,4),
    out_of_control  BOOLEAN      DEFAULT FALSE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_spc_measurement_period ON spc_statistics(measurement_name, period_start);

-- Traceability
CREATE TABLE IF NOT EXISTS assembly_record (
    id              BIGSERIAL PRIMARY KEY,
    robot_id        BIGINT       NOT NULL REFERENCES robot(id),
    station_id      BIGINT       NOT NULL,
    operator_id     VARCHAR(64)  NOT NULL,
    started_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    status          VARCHAR(16)  NOT NULL DEFAULT 'IN_PROGRESS',
    torque_curve_url VARCHAR(512),
    notes           TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_assembly_robot ON assembly_record(robot_id);

CREATE TABLE IF NOT EXISTS component_trace (
    id              BIGSERIAL PRIMARY KEY,
    robot_id        BIGINT       NOT NULL REFERENCES robot(id),
    material_id     BIGINT       NOT NULL,
    lot_number      VARCHAR(64)  NOT NULL,
    supplier_id     BIGINT,
    quantity        INT          NOT NULL DEFAULT 1,
    installed_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_trace_robot ON component_trace(robot_id);
CREATE INDEX IF NOT EXISTS idx_trace_lot ON component_trace(lot_number);

CREATE TABLE IF NOT EXISTS digital_passport (
    id              BIGSERIAL PRIMARY KEY,
    robot_id        BIGINT       NOT NULL UNIQUE REFERENCES robot(id),
    passport_data   JSONB        NOT NULL,
    pdf_url         VARCHAR(512),
    digital_signature TEXT,
    issued_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Logistics
CREATE TABLE IF NOT EXISTS serial_number_pool (
    id              BIGSERIAL PRIMARY KEY,
    prefix          VARCHAR(32)  NOT NULL,
    start_number    BIGINT       NOT NULL,
    end_number      BIGINT       NOT NULL,
    current_number  BIGINT       NOT NULL,
    status          VARCHAR(16)  NOT NULL DEFAULT 'ACTIVE',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS logistics_record (
    id              BIGSERIAL PRIMARY KEY,
    robot_id        BIGINT       NOT NULL,
    tracking_number VARCHAR(128),
    carrier         VARCHAR(64),
    from_location   VARCHAR(128),
    to_location     VARCHAR(128),
    status          VARCHAR(16)  NOT NULL DEFAULT 'PICKED',
    status_updated_at TIMESTAMPTZ DEFAULT NOW(),
    estimated_delivery DATE,
    actual_delivery DATE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Aftermarket
CREATE TABLE IF NOT EXISTS spare_part (
    id              BIGSERIAL PRIMARY KEY,
    material_id     BIGINT       NOT NULL,
    warehouse_code  VARCHAR(64)  NOT NULL,
    stock_quantity  INT          NOT NULL DEFAULT 0,
    safety_stock    INT          NOT NULL DEFAULT 0,
    reorder_point   INT          NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(material_id, warehouse_code)
);

CREATE TABLE IF NOT EXISTS repair_order (
    id              BIGSERIAL PRIMARY KEY,
    order_number    VARCHAR(64)  NOT NULL UNIQUE,
    robot_id        BIGINT       NOT NULL,
    customer_name   VARCHAR(128),
    fault_category  VARCHAR(64)  NOT NULL,
    fault_description TEXT,
    diagnosis_result TEXT,
    repair_action   TEXT,
    spare_parts_used JSONB,
    status          VARCHAR(16)  NOT NULL DEFAULT 'OPEN',
    priority        VARCHAR(8)   DEFAULT 'NORMAL',
    closed_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
