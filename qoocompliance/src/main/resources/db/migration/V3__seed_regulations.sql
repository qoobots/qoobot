-- ============================================================================
-- QooCompliance Database - V3: Seed regulation data
-- ============================================================================

-- CN regulations
INSERT INTO compliance_regulation (regulation_id, title, short_name, market, status, effective_date, impact_level)
VALUES ('CN-PIPL', '个人信息保护法', 'PIPL', 'CN', 'ACTIVE', '2021-11-01', 'HIGH')
ON CONFLICT (regulation_id) DO NOTHING;

INSERT INTO compliance_regulation (regulation_id, title, short_name, market, status, effective_date, impact_level)
VALUES ('CN-DSL', '数据安全法', 'DSL', 'CN', 'ACTIVE', '2021-09-01', 'HIGH')
ON CONFLICT (regulation_id) DO NOTHING;

INSERT INTO compliance_regulation (regulation_id, title, short_name, market, status, effective_date, impact_level)
VALUES ('CN-GENAI', '生成式AI服务管理规定', 'AI Regulation', 'CN', 'ACTIVE', '2023-08-15', 'MEDIUM')
ON CONFLICT (regulation_id) DO NOTHING;

-- EU regulations
INSERT INTO compliance_regulation (regulation_id, title, short_name, market, status, effective_date, impact_level)
VALUES ('EU-GDPR', '通用数据保护条例', 'GDPR', 'EU', 'ACTIVE', '2018-05-25', 'HIGH')
ON CONFLICT (regulation_id) DO NOTHING;

INSERT INTO compliance_regulation (regulation_id, title, short_name, market, status, effective_date, impact_level)
VALUES ('EU-AI-ACT', '人工智能法案', 'EU AI Act', 'EU', 'ACTIVE', '2024-08-01', 'CRITICAL')
ON CONFLICT (regulation_id) DO NOTHING;

INSERT INTO compliance_regulation (regulation_id, title, short_name, market, status, effective_date, impact_level)
VALUES ('EU-MDR', '机械法规', 'EU 2023/1230', 'EU', 'UPCOMING', '2027-01-20', 'HIGH')
ON CONFLICT (regulation_id) DO NOTHING;

-- US regulations
INSERT INTO compliance_regulation (regulation_id, title, short_name, market, status, effective_date, impact_level)
VALUES ('US-CCPA', '加州消费者隐私法案', 'CCPA/CPRA', 'US', 'ACTIVE', '2020-01-01', 'MEDIUM')
ON CONFLICT (regulation_id) DO NOTHING;

-- JP regulations
INSERT INTO compliance_regulation (regulation_id, title, short_name, market, status, effective_date, impact_level)
VALUES ('JP-APPI', '个人信息保护法', 'APPI', 'JP', 'ACTIVE', '2022-04-01', 'MEDIUM')
ON CONFLICT (regulation_id) DO NOTHING;
