-- Migration: Add doctor approval workflow fields to user_roles
-- Date: 2026-03-05

ALTER TABLE user_roles
ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) NOT NULL DEFAULT 'Approved';

ALTER TABLE user_roles
ADD COLUMN IF NOT EXISTS approved_by VARCHAR(255);

ALTER TABLE user_roles
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP;

ALTER TABLE user_roles
DROP CONSTRAINT IF EXISTS valid_user_approval_status;

ALTER TABLE user_roles
ADD CONSTRAINT valid_user_approval_status
CHECK (approval_status IN ('Pending', 'Approved', 'Rejected'));

CREATE INDEX IF NOT EXISTS idx_user_roles_hospital_role_status
ON user_roles(hospital_id, role, approval_status);
