-- V3: Production Line & Station seed data
-- Production Lines
INSERT INTO production_line (line_code, line_name, location, status, target_takt_sec, shift_per_day, operators_per_shift) VALUES
('L001', 'QooBot S Final Assembly Line',  'Building A, Floor 2', 'ACTIVE', 720, 2, 6),
('L002', 'QooBot S Sub-Assembly Line',    'Building A, Floor 1', 'ACTIVE', 360, 1, 4),
('L003', 'Calibration & Test Line',       'Building B, Floor 1', 'ACTIVE', 900, 2, 3);

-- Stations for L001 (Final Assembly)
INSERT INTO station (line_id, station_code, station_name, sequence_no, station_type, cycle_time_sec, tools_required, poka_yoke_enabled) VALUES
(1, 'ST-01', 'Frame Assembly',           1,  'ASSEMBLY',       300, 'Torque wrench 5-25Nm, Allen key set',           TRUE),
(1, 'ST-02', 'Joint Motor Installation', 2,  'ASSEMBLY',       420, 'Torque wrench 10-50Nm, Loctite 243',             TRUE),
(1, 'ST-03', 'Cable Routing & Dressing', 3,  'ASSEMBLY',       360, 'Cable tie gun, cable tester',                    TRUE),
(1, 'ST-04', 'Main Board Installation',  4,  'ASSEMBLY',       240, 'Torque screwdriver 0.5-2Nm, ESD mat',            TRUE),
(1, 'ST-05', 'Sensor Head Mounting',     5,  'ASSEMBLY',       300, 'Torque screwdriver, alignment fixture',           TRUE),
(1, 'ST-06', 'Shell & Cover Assembly',   6,  'ASSEMBLY',       180, 'Torque screwdriver, clip tool',                  TRUE),
(1, 'ST-07', 'Power-on Self Test',       7,  'TEST',           480, 'USB-C PD tester, multimeter, thermal camera',    TRUE),
(1, 'ST-08', 'Firmware Flash & Init',    8,  'TEST',           300, 'USB programmer, network cable',                  FALSE),
(1, 'ST-09', 'Functional Test',          9,  'TEST',           600, 'Test jig, reference markers, force gauge',       TRUE),
(1, 'ST-10', 'Final Inspection & Pack', 10,  'INSPECTION',     300, 'Appearance checklist, barcode scanner',          TRUE);

-- Stations for L002 (Sub-Assembly)
INSERT INTO station (line_id, station_code, station_name, sequence_no, station_type, cycle_time_sec, tools_required, poka_yoke_enabled) VALUES
(2, 'SB-01', 'PCB Soldering & Test',     1, 'ASSEMBLY',   180, 'Soldering station, microscope, multimeter', TRUE),
(2, 'SB-02', 'Motor-Gearbox Assembly',   2, 'ASSEMBLY',   240, 'Bearing press, grease dispenser, torque gauge', TRUE),
(2, 'SB-03', 'Sensor Pod Assembly',      3, 'ASSEMBLY',   200, 'Adhesive dispenser, UV curing lamp', TRUE);

-- Stations for L003 (Calibration & Test)
INSERT INTO station (line_id, station_code, station_name, sequence_no, station_type, cycle_time_sec, tools_required, poka_yoke_enabled) VALUES
(3, 'CT-01', 'Camera Calibration',       1, 'CALIBRATION', 600, 'Calibration board, robotic arm, lighting box', TRUE),
(3, 'CT-02', 'IMU Calibration',          2, 'CALIBRATION', 360, '6-axis rate table, temperature chamber', TRUE),
(3, 'CT-03', 'LiDAR-Camera Extrinsic',   3, 'CALIBRATION', 480, 'Checkerboard target, LiDAR target', TRUE),
(3, 'CT-04', 'Kinematic Calibration',    4, 'CALIBRATION', 900, 'Laser tracker, motion capture system', TRUE),
(3, 'CT-05', 'Force Sensor Calibration', 5, 'CALIBRATION', 360, '6-DOF force calibration rig', TRUE),
(3, 'CT-06', 'Calibration Verification', 6, 'VERIFICATION', 480, 'Reference objects, measurement arm', TRUE),
(3, 'CT-07', 'Burn-in Test',            7, 'BURN_IN',     720, 'Burn-in rack, power monitor, thermal logger', TRUE),
(3, 'CT-08', 'OQC Final Check',          8, 'INSPECTION',  300, 'Full inspection checklist, digital passport writer', TRUE);

-- SOP Steps for a key station (ST-01 Frame Assembly)
INSERT INTO sop_step (station_id, step_no, step_name, description, tool, time_sec, image_url, is_critical, warning) VALUES
(1, 1,  'Prepare workbench',    'Lay out ESD mat, check tools calibrated, verify kit completeness',                                   NULL,               60,  NULL,      FALSE, ''),
(1, 2,  'Inspect frame parts',  'Visually inspect all frame parts for scratches, dents, or machining defects',                        'Magnifying lamp',   60,  NULL,      TRUE,  'Reject if any visible defect found'),
(1, 3,  'Attach hip joint brackets', 'Bolt hip joint brackets to frame using M8 bolts',                                                'Torque wrench 15Nm', 120, NULL,      TRUE,  'Cross-tighten pattern; torque to 15±1 Nm'),
(1, 4,  'Install shoulder mounts',    'Secure shoulder servo mounts to upper frame',                                                   'Torque wrench 12Nm', 90,  NULL,      TRUE,  'Verify alignment with dowel pin'),
(1, 5,  'Verify frame geometry',      'Place frame on alignment fixture and check all key dimensions',                                'Alignment fixture',  120, NULL,      TRUE,  'Tolerance: ±0.2mm; if out of spec, disassemble and re-torque'),
(1, 6,  'Record serial & photo',      'Scan frame serial tag, take 4-angle photos for traceability',                                  'Barcode scanner, camera', 60, NULL, TRUE, 'Photos must be clear and include serial visible');

-- DFM Checklist items for QBS-001
INSERT INTO dfm_check (product_id, category, item, description, severity, status, reviewer, review_date, comment) VALUES
(1, 'MECHANICAL', 'Wall Thickness',          'Minimum wall thickness >= 2mm for CNC 7075-T6',               'MAJOR',   'PASS', 'alice.mech', '2026-03-10', 'All walls >= 2.5mm'),
(1, 'MECHANICAL', 'Undercut Analysis',       'No inaccessible undercuts requiring 5-axis repositioning',      'CRITICAL', 'PASS', 'alice.mech', '2026-03-10', 'Design is 3-axis compatible'),
(1, 'MECHANICAL', 'Thread Depth',            'Minimum thread engagement 1.5x nominal diameter',               'MAJOR',   'PASS', 'alice.mech', '2026-03-10', 'All threads >= 1.8x'),
(1, 'PCB',        'Component Spacing',       'Minimum 0.2mm clearance between 0201 components',               'CRITICAL', 'PASS', 'bob.ee',    '2026-03-12', 'Spacing verified in Altium'),
(1, 'PCB',        'Thermal Relief',          'Power components have adequate copper pour for heat dissipation', 'MAJOR', 'PASS', 'bob.ee',    '2026-03-12', 'Thermal simulation passed'),
(1, 'PCB',        'Test Point Coverage',     'All nets have accessible test points for ICT fixture',           'MINOR',   'PASS', 'bob.ee',    '2026-03-12', '100% coverage'),
(1, 'ASSEMBLY',   'Fastener Accessibility',  'All fasteners accessible with standard tools from one direction', 'MAJOR',  'PASS', 'charlie.mfg','2026-03-14', '2 fasteners need 90° adapter'),
(1, 'ASSEMBLY',   'Poka-Yoke Design',        'Asymmetric connectors prevent reverse insertion',                'CRITICAL', 'PASS', 'charlie.mfg','2026-03-14', 'All connectors keyed'),
(1, 'ASSEMBLY',   'Cable Routing Path',      'Cable routing paths defined and clip points marked on frame',    'MAJOR',   'PASS', 'charlie.mfg','2026-03-14', 'Routing guide included in drawings');

-- Alternate materials for critical components
INSERT INTO material_alternative (material_id, alternative_material_id, compatibility_score, verified) VALUES
(1,  NULL, 80, FALSE),  -- SoC: no direct alternative (sole-source)
(2,  NULL, 0,  FALSE),  -- D455: currently sole-source
(5,  NULL, 0,  FALSE),  -- QJ-80: custom motor, no alternative
(7,  NULL, 0,  FALSE);  -- Battery: custom pack, CATL sole-source
