-- Migration: Add prescription state management and workflow columns
-- Date: 2026-03-05
-- Spec: seva-arogya-prescription-enhancement
-- Task: 1.1 Create database migration script for prescription state management
-- Requirements: 1.1, 1.2, 1.5, 1.7, 21.1, 21.3, 21.4

-- Add state management columns to prescriptions table
ALTER TABLE prescriptions
ADD COLUMN IF NOT EXISTS state VARCHAR(50) NOT NULL DEFAULT 'Draft',
ADD COLUMN IF NOT EXISTS created_by_doctor_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS finalized_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS finalized_by VARCHAR(255),
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS deleted_by VARCHAR(255),
ADD COLUMN IF NOT EXISTS pre_deleted_state VARCHAR(50);

-- Add constraint to ensure state is one of the valid values
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'valid_prescription_state'
    ) THEN
        ALTER TABLE prescriptions
        ADD CONSTRAINT valid_prescription_state 
        CHECK (state IN ('Draft', 'InProgress', 'Finalized', 'Deleted'));
    END IF;
END $$;

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_prescriptions_state ON prescriptions(state);
CREATE INDEX IF NOT EXISTS idx_prescriptions_deleted_at ON prescriptions(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_prescriptions_created_by_doctor ON prescriptions(created_by_doctor_id);

-- Backfill created_by_doctor_id from user_id for existing prescriptions
UPDATE prescriptions 
SET created_by_doctor_id = user_id 
WHERE created_by_doctor_id IS NULL;

-- Make created_by_doctor_id NOT NULL after backfill
ALTER TABLE prescriptions
ALTER COLUMN created_by_doctor_id SET NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN prescriptions.state IS 'Prescription workflow state: Draft, InProgress, Finalized, or Deleted';
COMMENT ON COLUMN prescriptions.created_by_doctor_id IS 'Doctor who created this prescription';
COMMENT ON COLUMN prescriptions.finalized_at IS 'Timestamp when prescription was finalized';
COMMENT ON COLUMN prescriptions.finalized_by IS 'User ID who finalized the prescription';
COMMENT ON COLUMN prescriptions.deleted_at IS 'Timestamp when prescription was soft deleted';
COMMENT ON COLUMN prescriptions.deleted_by IS 'User ID who deleted the prescription';
COMMENT ON COLUMN prescriptions.pre_deleted_state IS 'State before deletion for restore functionality';
