# Database Migrations

This directory contains SQL migration scripts for the SEVA Arogya database schema.

## Running Migrations

### Prerequisites
- Database connection configured in `.env` file
- Python environment with required dependencies installed

### Run a Migration

```bash
python migrations/run_migration.py migrations/001_add_streaming_columns.sql
```

## Available Migrations

### 001_add_streaming_columns.sql
Adds support for real-time streaming transcription:
- `session_id` - WebSocket session identifier
- `streaming_job_id` - AWS Transcribe streaming session ID
- `is_streaming` - Flag for streaming vs batch transcriptions
- `partial_transcript` - Last partial result for recovery
- `audio_duration_seconds` - Total audio duration
- `sample_rate` - Audio sample rate (8000, 16000, 48000 Hz)
- `quality` - Quality setting (low, medium, high)

**Run this migration before using the live transcription streaming feature.**

## Migration Naming Convention

Migrations are numbered sequentially:
- `001_description.sql`
- `002_description.sql`
- etc.

## Rollback

To rollback a migration, create a corresponding rollback script:
- `001_add_streaming_columns_rollback.sql`

Example rollback:
```sql
ALTER TABLE transcriptions
DROP COLUMN IF EXISTS session_id,
DROP COLUMN IF EXISTS streaming_job_id,
DROP COLUMN IF EXISTS is_streaming,
DROP COLUMN IF EXISTS partial_transcript,
DROP COLUMN IF EXISTS audio_duration_seconds,
DROP COLUMN IF EXISTS sample_rate,
DROP COLUMN IF EXISTS quality;

DROP INDEX IF EXISTS idx_transcriptions_session_id;
DROP INDEX IF EXISTS idx_transcriptions_streaming_job_id;
DROP INDEX IF EXISTS idx_transcriptions_is_streaming;
```
