-- Migration: Add chunk_sequence column for tracking audio chunk order within clips
-- Date: 2026-03-02
-- Spec: async-push-to-talk-transcription
-- Task: 1.1 Add consultation and transcription clip ordering fields

-- Add chunk_sequence column to transcriptions table
ALTER TABLE transcriptions
ADD COLUMN IF NOT EXISTS chunk_sequence INTEGER DEFAULT 1;

-- Create composite index for efficient querying by consultation_id and clip_order
-- This index already exists from migration 002, but we ensure it's present
CREATE INDEX IF NOT EXISTS idx_transcriptions_consultation_clip_order
ON transcriptions(consultation_id, clip_order);

-- Create index for chunk_sequence within a clip (for ordering chunks)
CREATE INDEX IF NOT EXISTS idx_transcriptions_clip_chunks
ON transcriptions(consultation_id, clip_order, chunk_sequence);

-- Add comments for documentation
COMMENT ON COLUMN transcriptions.chunk_sequence IS 'Order of audio chunk within a clip for chunked streaming transcription';
