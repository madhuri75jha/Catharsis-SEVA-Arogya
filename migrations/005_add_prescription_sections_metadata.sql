-- Migration: Add prescription sections and metadata columns
-- Date: 2026-03-05
-- Spec: seva-arogya-prescription-enhancement
-- Task: 1.2 Create database migration for prescription sections and metadata
-- Requirements: 2.2, 21.2, 21.5, 21.7, 21.8

-- Add sections and metadata columns to prescriptions table
ALTER TABLE prescriptions
ADD COLUMN IF NOT EXISTS sections JSONB NOT NULL DEFAULT '[]',
ADD COLUMN IF NOT EXISTS bedrock_payload JSONB,
ADD COLUMN IF NOT EXISTS consultation_id VARCHAR(64),
ADD COLUMN IF NOT EXISTS hospital_id VARCHAR(64) NOT NULL DEFAULT 'default',
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_prescriptions_hospital_id ON prescriptions(hospital_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_consultation_id ON prescriptions(consultation_id);

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_prescription_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_prescription_timestamp ON prescriptions;
CREATE TRIGGER trigger_update_prescription_timestamp
    BEFORE UPDATE ON prescriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_prescription_timestamp();

-- Add comments for documentation
COMMENT ON COLUMN prescriptions.sections IS 'Array of prescription sections with key, title, content, status, and order';
COMMENT ON COLUMN prescriptions.bedrock_payload IS 'Raw Bedrock AI response payload for audit purposes';
COMMENT ON COLUMN prescriptions.consultation_id IS 'Link to consultation session for audio/transcription';
COMMENT ON COLUMN prescriptions.hospital_id IS 'Hospital where prescription was created';
COMMENT ON COLUMN prescriptions.updated_at IS 'Timestamp of last update (auto-updated)';
