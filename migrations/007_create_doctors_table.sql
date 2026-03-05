-- Migration: Create doctors table for doctor profiles and hospital associations
-- Date: 2026-03-05
-- Spec: seva-arogya-prescription-enhancement
-- Task: 1.4 Create doctors table and associations
-- Requirements: 15.2, 15.3, 15.4

-- Create doctors table
CREATE TABLE IF NOT EXISTS doctors (
    doctor_id VARCHAR(255) PRIMARY KEY,
    hospital_id VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    specialty VARCHAR(255),
    signature_url VARCHAR(512),
    availability TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE RESTRICT
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_doctors_hospital_id ON doctors(hospital_id);

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_doctor_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_doctor_timestamp ON doctors;
CREATE TRIGGER trigger_update_doctor_timestamp
    BEFORE UPDATE ON doctors
    FOR EACH ROW
    EXECUTE FUNCTION update_doctor_timestamp();

-- Add comments for documentation
COMMENT ON TABLE doctors IS 'Doctor profiles and hospital associations';
COMMENT ON COLUMN doctors.doctor_id IS 'Unique doctor identifier (matches Cognito user_id)';
COMMENT ON COLUMN doctors.hospital_id IS 'Hospital where doctor practices';
COMMENT ON COLUMN doctors.name IS 'Doctor full name';
COMMENT ON COLUMN doctors.specialty IS 'Medical specialty (e.g., Cardiology, Pediatrics)';
COMMENT ON COLUMN doctors.signature_url IS 'S3 URL for doctor signature image';
COMMENT ON COLUMN doctors.availability IS 'Doctor availability schedule (display only)';
