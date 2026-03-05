-- Migration: Create hospitals table for hospital management
-- Date: 2026-03-05
-- Spec: seva-arogya-prescription-enhancement
-- Task: 1.3 Create hospitals table and seed data
-- Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7

-- Create hospitals table
CREATE TABLE IF NOT EXISTS hospitals (
    hospital_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    phone VARCHAR(50),
    email VARCHAR(255),
    registration_number VARCHAR(100),
    website VARCHAR(255),
    logo_url VARCHAR(512),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_hospital_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_hospital_timestamp ON hospitals;
CREATE TRIGGER trigger_update_hospital_timestamp
    BEFORE UPDATE ON hospitals
    FOR EACH ROW
    EXECUTE FUNCTION update_hospital_timestamp();

-- Add comments for documentation
COMMENT ON TABLE hospitals IS 'Hospital information for prescription headers and management';
COMMENT ON COLUMN hospitals.hospital_id IS 'Unique hospital identifier';
COMMENT ON COLUMN hospitals.name IS 'Hospital name';
COMMENT ON COLUMN hospitals.address IS 'Hospital physical address';
COMMENT ON COLUMN hospitals.phone IS 'Hospital contact phone number';
COMMENT ON COLUMN hospitals.email IS 'Hospital contact email';
COMMENT ON COLUMN hospitals.registration_number IS 'Hospital registration/license number';
COMMENT ON COLUMN hospitals.website IS 'Hospital website URL';
COMMENT ON COLUMN hospitals.logo_url IS 'S3 URL for hospital logo image';

-- Insert default hospital for existing prescriptions
INSERT INTO hospitals (hospital_id, name, address, phone, email)
VALUES ('default', 'SEVA Arogya Hospital', '123 Healthcare Street, Medical District', '+91-1234567890', 'info@sevaarogya.com')
ON CONFLICT (hospital_id) DO NOTHING;

-- Add foreign key constraint from prescriptions to hospitals
ALTER TABLE prescriptions
DROP CONSTRAINT IF EXISTS fk_prescriptions_hospital;

ALTER TABLE prescriptions
ADD CONSTRAINT fk_prescriptions_hospital
FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id)
ON DELETE RESTRICT;
