# SEVA Arogya ER Diagram

```mermaid
erDiagram
    CONSULTATIONS {
        varchar consultation_id PK
        varchar user_id
        varchar status
        text merged_transcript_text
        timestamp created_at
        timestamp updated_at
    }

    TRANSCRIPTIONS {
        int transcription_id PK
        varchar user_id
        varchar audio_s3_key
        varchar job_id UK
        text transcript_text
        varchar status
        jsonb medical_entities
        varchar session_id
        varchar streaming_job_id
        boolean is_streaming
        text partial_transcript
        float audio_duration_seconds
        int sample_rate
        varchar quality
        varchar consultation_id
        int clip_order
        int chunk_sequence
        timestamp created_at
        timestamp updated_at
    }

    PRESCRIPTIONS {
        int prescription_id PK
        varchar user_id
        varchar patient_name
        jsonb medications
        varchar s3_key
        varchar state
        varchar created_by_doctor_id
        timestamp finalized_at
        varchar finalized_by
        timestamp deleted_at
        varchar deleted_by
        varchar pre_deleted_state
        jsonb sections
        jsonb bedrock_payload
        varchar consultation_id
        varchar hospital_id
        timestamp created_at
        timestamp updated_at
    }

    HOSPITALS {
        varchar hospital_id PK
        varchar name
        text address
        varchar phone
        varchar email
        varchar registration_number
        varchar website
        varchar logo_url
        timestamp created_at
        timestamp updated_at
    }

    DOCTORS {
        varchar doctor_id PK
        varchar hospital_id
        varchar name
        varchar specialty
        varchar signature_url
        text availability
        timestamp created_at
        timestamp updated_at
    }

    USER_ROLES {
        varchar user_id PK
        varchar role
        varchar hospital_id
        timestamp created_at
        timestamp updated_at
    }

    SCHEMA_MIGRATIONS {
        int id PK
        varchar migration_name
        timestamp applied_at
    }

    HOSPITALS ||--o{ PRESCRIPTIONS : "hospital_id (FK)"
    HOSPITALS ||--o{ DOCTORS : "hospital_id (FK)"

    CONSULTATIONS ||--o{ TRANSCRIPTIONS : "consultation_id (logical)"
    CONSULTATIONS ||--o{ PRESCRIPTIONS : "consultation_id (logical)"
    DOCTORS ||--o{ PRESCRIPTIONS : "created_by_doctor_id (logical)"
    HOSPITALS ||--o{ USER_ROLES : "hospital_id (logical)"
```

## Notes
- Explicit foreign keys in migrations:
  - `prescriptions.hospital_id -> hospitals.hospital_id`
  - `doctors.hospital_id -> hospitals.hospital_id`
- Important logical links (used in application queries/workflow):
  - `transcriptions.consultation_id -> consultations.consultation_id`
  - `prescriptions.consultation_id -> consultations.consultation_id`
  - `prescriptions.created_by_doctor_id -> doctors.doctor_id`
  - `user_roles.hospital_id -> hospitals.hospital_id` (not enforced by FK)
- Key check constraints:
  - `prescriptions.state IN ('Draft', 'InProgress', 'Finalized', 'Deleted')`
  - `user_roles.role IN ('Doctor', 'HospitalAdmin', 'DeveloperAdmin')`
- Notable defaults:
  - `transcriptions.is_streaming = false`, `sample_rate = 16000`, `quality = 'medium'`
  - `prescriptions.hospital_id = 'default'` (then constrained by FK)
