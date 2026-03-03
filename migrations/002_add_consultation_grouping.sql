-- Migration: Add consultation-level grouping for multi-clip audio sessions
-- Date: 2026-03-02

CREATE TABLE IF NOT EXISTS consultations (
    consultation_id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'IN_PROGRESS',
    merged_transcript_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_consultations_user_id ON consultations(user_id);
CREATE INDEX IF NOT EXISTS idx_consultations_created_at ON consultations(created_at DESC);

ALTER TABLE transcriptions
ADD COLUMN IF NOT EXISTS consultation_id VARCHAR(64),
ADD COLUMN IF NOT EXISTS clip_order INTEGER DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_transcriptions_consultation_id ON transcriptions(consultation_id);
CREATE INDEX IF NOT EXISTS idx_transcriptions_consultation_clip_order
ON transcriptions(consultation_id, clip_order);

COMMENT ON TABLE consultations IS 'Consultation-level container for one visit/session with multiple audio clips';
COMMENT ON COLUMN consultations.merged_transcript_text IS 'Final merged transcript across all clips in consultation';
COMMENT ON COLUMN transcriptions.consultation_id IS 'Parent consultation identifier for this audio clip';
COMMENT ON COLUMN transcriptions.clip_order IS 'Order of clip capture within consultation';
