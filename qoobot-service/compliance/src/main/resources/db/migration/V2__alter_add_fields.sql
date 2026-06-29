-- ============================================================================
-- QooCompliance Database Schema - V2: Add missing fields
-- ============================================================================

ALTER TABLE compliance_item ADD COLUMN IF NOT EXISTS market VARCHAR(8);
ALTER TABLE compliance_checklist ADD COLUMN IF NOT EXISTS target_markets VARCHAR(128);
ALTER TABLE compliance_regulation ADD COLUMN IF NOT EXISTS impact_level VARCHAR(32);
ALTER TABLE regulation_change ADD COLUMN IF NOT EXISTS market VARCHAR(8);
