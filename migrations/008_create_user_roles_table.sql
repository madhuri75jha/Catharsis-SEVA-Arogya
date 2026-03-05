-- Migration: Create user_roles table for role-based access control
-- Date: 2026-03-05
-- Spec: seva-arogya-prescription-enhancement
-- Task: 1.5 Create user_roles table for RBAC
-- Requirements: 8.1, 8.2, 8.3, 20.6, 20.7

-- Create user_roles table
CREATE TABLE IF NOT EXISTS user_roles (
    user_id VARCHAR(255) PRIMARY KEY,
    role VARCHAR(50) NOT NULL,
    hospital_id VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_user_role CHECK (role IN ('Doctor', 'HospitalAdmin', 'DeveloperAdmin'))
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_user_roles_hospital_id ON user_roles(hospital_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles(role);

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_role_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_user_role_timestamp ON user_roles;
CREATE TRIGGER trigger_update_user_role_timestamp
    BEFORE UPDATE ON user_roles
    FOR EACH ROW
    EXECUTE FUNCTION update_user_role_timestamp();

-- Add comments for documentation
COMMENT ON TABLE user_roles IS 'User role assignments for role-based access control';
COMMENT ON COLUMN user_roles.user_id IS 'User identifier (matches Cognito user_id)';
COMMENT ON COLUMN user_roles.role IS 'User role: Doctor, HospitalAdmin, or DeveloperAdmin';
COMMENT ON COLUMN user_roles.hospital_id IS 'Hospital association (NULL for DeveloperAdmin)';
COMMENT ON CONSTRAINT valid_user_role ON user_roles IS 'Ensures role is one of the three valid values';
