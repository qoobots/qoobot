-- V3: Orders & Licenses
CREATE TABLE IF NOT EXISTS orders (
    id BIGSERIAL PRIMARY KEY,
    order_no VARCHAR(64) NOT NULL UNIQUE,
    user_id UUID NOT NULL,
    skill_id BIGINT NOT NULL REFERENCES skills(id),
    version_id BIGINT REFERENCES skill_versions(id),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    discount_amount DECIMAL(10,2) DEFAULT 0.00,
    tax_amount DECIMAL(10,2) DEFAULT 0.00,
    total_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(16) DEFAULT 'pending',
    payment_method VARCHAR(32),
    payment_id VARCHAR(255),
    paid_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS licenses (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    skill_id BIGINT NOT NULL REFERENCES skills(id),
    version_id BIGINT REFERENCES skill_versions(id),
    order_id BIGINT REFERENCES orders(id),
    device_id VARCHAR(128),
    license_key VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(16) DEFAULT 'perpetual',
    status VARCHAR(16) DEFAULT 'active',
    starts_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, skill_id, device_id)
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_order_no ON orders(order_no);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_licenses_user_id ON licenses(user_id);
CREATE INDEX idx_licenses_device_id ON licenses(device_id);
