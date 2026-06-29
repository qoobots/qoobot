-- V2: BOM & Supplier seed data for development
-- Products
INSERT INTO product (model_code, model_name, category, status) VALUES
('QBS-001',  'QooBot S Standard',     'BIPEDAL',    'ACTIVE'),
('QBS-001P', 'QooBot S Pro',          'BIPEDAL',    'ACTIVE'),
('QBW-001',  'QooBot Wheeled Base',   'WHEELED',    'ACTIVE');

-- Materials
INSERT INTO material (material_code, material_name, category, specification, manufacturer, manufacturer_pn, lifecycle, lead_time_days, moq, rohs_compliant, reach_compliant) VALUES
('CPU-001',    'Qualcomm QCS8550 SoC',            'SEMICONDUCTOR', '8-core, 4nm, NPU 48 TOPS',   'Qualcomm',   'QCS-8550',  'ACTIVE', 90, 1000, TRUE, TRUE),
('SENS-001',   'Intel RealSense D455',             'SENSOR',        'RGB-D 1280x720@90fps',         'Intel',      'D455',      'ACTIVE', 30, 100,  TRUE, TRUE),
('SENS-002',   'Livox Mid-360 LiDAR',              'SENSOR',        '360° FoV, 40m range',          'Livox',      'Mid-360',   'ACTIVE', 45, 50,   TRUE, TRUE),
('SENS-003',   'Bosch BMI270 IMU',                 'SENSOR',        '6-axis, 16-bit',               'Bosch',      'BMI270',    'ACTIVE', 30, 500,  TRUE, TRUE),
('MOTOR-001',  'QJ-80 Joint Motor',                'ACTUATOR',      '80Nm peak, 36V, FOC',          'QJ Series',  'QJ-80-R1',  'ACTIVE', 60, 200,  TRUE, TRUE),
('MOTOR-002',  'QJ-50 Joint Motor',                'ACTUATOR',      '50Nm peak, 24V, FOC',          'QJ Series',  'QJ-50-R1',  'ACTIVE', 60, 300,  TRUE, TRUE),
('PWR-001',    'Li-Po 48V 20Ah Battery Pack',       'POWER',        '48V 20Ah, BMS built-in',       'CATL',       'QB-PACK-48', 'ACTIVE', 45, 100,  TRUE, TRUE),
('PCB-001',    'QooBot Main Control Board v2.3',    'PCB',          '6-layer, ENIG, impedance ctrl', 'QooPCB',    'QB-MCB-23', 'ACTIVE', 20, 500,  TRUE, TRUE),
('STR-001',    'Aluminum 7075-T6 Frame Set',        'STRUCTURAL',   'CNC machined, anodized',        'QooFab',     'QB-FRAME',  'ACTIVE', 30, 50,   TRUE, TRUE),
('STR-002',    'Carbon Fiber Shell Panel',          'STRUCTURAL',   '3K twill, 2mm thick',           'QooFab',     'QB-SHELL',  'ACTIVE', 25, 100,  TRUE, TRUE),
('CABLE-001',  'FPC Flat Cable 40-pin 0.5mm',       'CABLE',        '40-pin, 0.5mm pitch, 150mm',   'Molex',      '15039-0400', 'ACTIVE', 15, 1000, TRUE, TRUE),
('CONN-001',   'USB-C PD 3.0 Connector',            'CONNECTOR',    'USB-C PD 100W, IP67',          'Amphenol',   'USB-C-PD-100', 'ACTIVE', 20, 500, TRUE, TRUE);

-- Suppliers
INSERT INTO supplier (supplier_code, supplier_name, category, country, rating, status, contact_name, contact_email, contact_phone, audit_date) VALUES
('SUP-001', 'Qualcomm Technologies',         'SEMICONDUCTOR', 'USA',   5, 'QUALIFIED', 'John Wang',   'john.wang@qualcomm.com',   '+1-858-555-0100', '2025-12-15'),
('SUP-002', 'Intel Corporation',             'SENSOR',        'USA',   5, 'QUALIFIED', 'Sarah Lin',   'sarah.lin@intel.com',      '+1-408-555-0200', '2025-11-20'),
('SUP-003', 'Livox Technology',              'SENSOR',        'China', 4, 'QUALIFIED', 'Chen Wei',    'chen.wei@livoxtech.com',   '+86-755-555-0300', '2025-12-01'),
('SUP-004', 'Bosch Sensortec',               'SENSOR',        'Germany', 5,'QUALIFIED', 'Hans Mueller', 'h.mueller@bosch.com',     '+49-711-555-0400', '2025-10-15'),
('SUP-005', 'QJ Series Motors',              'ACTUATOR',      'China', 4, 'QUALIFIED', 'Zhang Tao',   'zhangtao@qj-motor.cn',     '+86-512-555-0500', '2025-12-10'),
('SUP-006', 'CATL (Contemporary Amperex)',    'POWER',        'China', 5, 'QUALIFIED', 'Li Ming',     'liming@catl.com',          '+86-593-555-0600', '2025-12-05'),
('SUP-007', 'QooPCB Manufacturing',           'PCB',           'China', 3, 'PROBATION', 'Huang Lei',  'huanglei@qoopcb.cn',       '+86-755-555-0700', '2026-01-10'),
('SUP-008', 'QooFab Precision',               'STRUCTURAL',    'China', 4, 'QUALIFIED', 'Liu Yang',   'liuyang@qoofab.cn',        '+86-512-555-0800', '2025-11-25');

-- BOM for QBS-001
INSERT INTO bom (product_id, version, bom_type, status, total_items, estimated_cost, cost_currency, released_at, created_by) VALUES
(1, '2.3', 'EBOM', 'RELEASED', 12, 15200.00, 'CNY', '2026-03-15', 'charlie.eng'),
(1, '2.3', 'MBOM', 'DRAFT',    12, 15200.00, 'CNY', NULL,          'peter.mfg');

-- BOM Items (QBS-001 EBOM v2.3)
INSERT INTO bom_item (bom_id, item_code, item_name, level, quantity, unit, material_id, is_critical, sort_order) VALUES
(1, 'QB-001-00', 'QooBot S Complete Assembly', 0, 1,    'SET', NULL,       TRUE,  0),
(1, 'QB-001-01', 'Main Control Board Assembly', 1, 1,    'PCS', NULL,       TRUE,  1),
(1, 'QB-001-02', 'Joint Drive Assembly',        1, 12,   'PCS', NULL,       TRUE,  2),
(1, 'QB-001-03', 'Sensor Head Assembly',        1, 1,    'PCS', NULL,       TRUE,  3),
(1, 'QB-001-04', 'Power System Assembly',       1, 1,    'PCS', NULL,       TRUE,  4),
(1, 'QB-001-05', 'Structural Assembly',         1, 1,    'PCS', NULL,       TRUE,  5),
(1, 'QB-001-11', 'Qualcomm QCS8550 SoC',        2, 1,    'PCS', 1,          TRUE,  10),
(1, 'QB-001-12', 'Main Control Board PCB',      2, 1,    'PCS', 8,          TRUE,  11),
(1, 'QB-001-21', 'QJ-80 Joint Motor',           2, 4,    'PCS', 5,          TRUE,  20),
(1, 'QB-001-22', 'QJ-50 Joint Motor',           2, 8,    'PCS', 6,          TRUE,  21),
(1, 'QB-001-31', 'Intel RealSense D455',        2, 1,    'PCS', 2,          TRUE,  30),
(1, 'QB-001-32', 'Livox Mid-360 LiDAR',         2, 1,    'PCS', 3,          TRUE,  31),
(1, 'QB-001-33', 'Bosch BMI270 IMU',            2, 2,    'PCS', 4,          FALSE, 32),
(1, 'QB-001-41', 'Li-Po 48V 20Ah Battery',      2, 1,    'PCS', 7,          TRUE,  40),
(1, 'QB-001-51', 'Aluminum 7075-T6 Frame Set',  2, 1,    'SET', 9,          TRUE,  50),
(1, 'QB-001-52', 'Carbon Fiber Shell Panel',    2, 2,    'PCS', 10,         FALSE, 51);

-- Material-Supplier relationships
INSERT INTO material_supplier (material_id, supplier_id, is_preferred, unit_price, currency, min_order_qty, lead_time_days, last_updated) VALUES
(1,  1,  TRUE,  120.00, 'USD', 1000, 90, '2026-03-01'),
(2,  2,  TRUE,  349.00, 'USD', 100,  30, '2026-02-15'),
(3,  3,  TRUE,  520.00, 'USD', 50,   45, '2026-01-20'),
(4,  4,  TRUE,    2.80, 'USD', 500,  30, '2026-03-01'),
(5,  5,  TRUE,  450.00, 'USD', 200,  60, '2026-02-01'),
(6,  5,  TRUE,  280.00, 'USD', 300,  60, '2026-02-01'),
(7,  6,  TRUE,  180.00, 'USD', 100,  45, '2026-03-10'),
(8,  7,  TRUE,   45.00, 'USD', 500,  20, '2026-03-15'),
(9,  8,  TRUE, 1200.00, 'USD', 50,   30, '2026-02-20'),
(10, 8,  TRUE,   85.00, 'USD', 100,  25, '2026-02-20');
