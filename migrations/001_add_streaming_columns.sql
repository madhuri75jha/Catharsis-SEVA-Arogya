-- Migration: Add streaming transcription support columns
-- Date: 2024-01-01
-- Description: Adds columns to support real-time streaming transcription with AWS Transcribe

-- Add streaming-specific columns to transcriptions table
ALTER TABLE transcriptions
ADD COLUMN IF NOT EXISTS session_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS streaming_job_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS is_streaming BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS partial_transcript TEXT,
ADD COLUMN IF NOT EXISTS audio_duration_seconds FLOAT,
ADD COLUMN IF NOT EXISTS sample_rate INTEGER DEFAULT 16000,
ADD COLUMN IF NOT EXISTS quality VARCHAR(20) DEFAULT 'medium';

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_transcriptions_session_id ON transcriptions(session_id);
CREATE INDEX IF NOT EXISTS idx_transcriptions_streaming_job_id ON transcriptions(streaming_job_id);
CREATE INDEX IF NOT EXISTS idx_transcriptions_is_streaming ON transcriptions(is_streaming);

-- Add comment to document the migration
COMMENT ON COLUMN transcriptions.session_id IS 'Unique identifier for WebSocket session';
COMMENT ON COLUMN transcriptions.streaming_job_id IS 'AWS Transcribe streaming session ID';
COMMENT ON COLUMN transcriptions.is_streaming IS 'Flag to distinguish streaming vs batch transcriptions';
COMMENT ON COLUMN transcriptions.partial_transcript IS 'Last partial result for recovery/debugging';
COMMENT ON COLUMN transcriptions.audio_duration_seconds IS 'Total duration of audio captured in seconds';
COMMENT ON COLUMN transcriptions.sample_rate IS 'Audio sample rate used (8000, 16000, or 48000 Hz)';
COMMENT ON COLUMN transcriptions.quality IS 'Quality setting: low (8kHz), medium (16kHz), high (48kHz)';
