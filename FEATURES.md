# SEVA Arogya - Feature Documentation

**Version:** 2.0  
**Last Updated:** March 8, 2026

---

## 📋 Table of Contents

1. [Bedrock Medical Extraction](#bedrock-medical-extraction)
2. [Streaming Transcription](#streaming-transcription)
3. [Prescription Workflow](#prescription-workflow)
4. [Hospital Management](#hospital-management)
5. [Role-Based Access Control](#role-based-access-control)
6. [CloudWatch Logs Viewer](#cloudwatch-logs-viewer)

---

## 1. Bedrock Medical Extraction

### Overview

AI-powered prescription generation using Amazon Bedrock (Claude 3) with function calling for structured data extraction.

### Implementation Status: ✅ Complete

**Components:**
- `aws_services/bedrock_client.py` - Bedrock integration
- `aws_services/comprehend_manager.py` - Entity extraction
- `aws_services/extraction_pipeline.py` - Orchestration
- `aws_services/validation_layer.py` - Data validation
- `aws_services/config_manager.py` - Hospital configurations
- `models/bedrock_extraction.py` - Pydantic models

### How It Works

```
Transcript Text
    ↓
[Comprehend Medical] → Extract entities (medications, symptoms, diagnoses)
    ↓
[Hospital Config] → Load field definitions and validation rules
    ↓
[Bedrock Claude 3] → Function calling to map entities to fields
    ↓
[Validation Layer] → Normalize dosages, validate fields
    ↓
Structured Prescription with Confidence Scores
```

### API Endpoints

```bash
# Extract prescription from transcript
POST /api/v1/extract
Content-Type: application/json
{
  "transcript": "Patient has fever. Prescribed paracetamol 500mg.",
  "hospital_id": "hosp_123"
}

# Response
{
  "success": true,
  "extraction": {
    "patient_details": {...},
    "vitals": {...},
    "diagnosis": {...},
    "medications": [...],
    "clinical_notes": {...}
  },
  "confidence_scores": {...},
  "processing_time_ms": 2500
}

# Get hospital configuration
GET /api/v1/config/<hospital_id>
```

### Hospital Configuration

Configurations stored in `config/hospitals/<hospital_id>.json`:

```json
{
  "hospital_id": "hosp_123",
  "hospital_name": "City General Hospital",
  "sections": {
    "patient_details": {
      "fields": {
        "name": {
          "type": "text",
          "required": true,
          "description": "Patient's full name"
        },
        "age": {
          "type": "number",
          "required": true,
          "validation": {"min": 0, "max": 150}
        }
      }
    },
    "medications": {
      "repeatable": true,
      "fields": {
        "medication_name": {"type": "text", "required": true},
        "dosage": {"type": "text", "required": true},
        "frequency": {"type": "text", "required": true},
        "duration": {"type": "text", "required": true}
      }
    }
  }
}
```

### Confidence Indicators

- 🟢 **Green (>80%):** High confidence, likely accurate
- 🟡 **Yellow (50-80%):** Medium confidence, review recommended
- 🔴 **Red (<50%):** Low confidence, manual verification required
- ⚪ **Gray:** Manual entry, no AI extraction

### Features

- **Dynamic Form Generation:** Forms rendered from JSON configuration
- **Hospital-Specific Fields:** Customizable per hospital
- **Repeatable Sections:** Add/remove medication entries
- **Source Context:** View transcript excerpt for each field
- **Editable Fields:** All fields remain editable after auto-fill
- **Validation:** Client and server-side validation

### Cost

Per prescription extraction:
- Comprehend Medical: ~$0.10 (1000 chars)
- Bedrock (Claude 3 Sonnet): ~$0.05-0.10
- **Total: ~$0.15-0.20**

### Quick Start

```bash
# 1. Configure Bedrock
export BEDROCK_REGION=us-east-1
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# 2. Test extraction
curl -X POST http://localhost:5000/api/v1/extract \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d @sample_transcript.json

# 3. Navigate to AI-assisted prescription page
# http://localhost:5000/bedrock-prescription
```

---

## 2. Streaming Transcription

### Overview

Real-time audio transcription using Amazon Transcribe Medical with WebSocket streaming.

### Implementation Status: ✅ Complete

**Components:**
- `aws_services/transcribe_streaming_manager.py` - Streaming client
- `aws_services/transcription_queue_manager.py` - Queue management
- `aws_services/consultation_session_manager.py` - Session tracking
- `socketio_handlers.py` - WebSocket handlers
- `templates/live_transcription.html` - Frontend UI

### How It Works

```
Microphone → Web Audio API → Chunks (16kHz mono)
    ↓
WebSocket (Socket.IO) → Flask Backend
    ↓
Amazon Transcribe Medical Streaming API
    ↓
Real-time Transcript Events
    ↓
WebSocket → Frontend Display
```

### WebSocket Events

**Client → Server:**
```javascript
// Start session
socket.emit('start_transcription_session', {
  consultation_id: 'cons_123'
});

// Send audio chunk
socket.emit('audio_chunk', {
  audio: base64EncodedAudio,
  consultation_id: 'cons_123'
});

// Stop session
socket.emit('stop_transcription_session', {
  consultation_id: 'cons_123'
});
```

**Server → Client:**
```javascript
// Transcript update
socket.on('transcript_update', (data) => {
  console.log(data.transcript);  // Partial transcript
  console.log(data.is_final);    // true if segment complete
});

// Session complete
socket.on('transcription_complete', (data) => {
  console.log(data.full_transcript);
  console.log(data.consultation_id);
});

// Error
socket.on('transcription_error', (data) => {
  console.error(data.error);
});
```

### Features

- **Real-time Transcription:** < 2 second latency
- **Medical Vocabulary:** Optimized for clinical terms
- **Accent Support:** Indian English recognition
- **Session Management:** Multiple concurrent sessions
- **Queue Management:** Max 10 concurrent jobs
- **Retry Logic:** Automatic retry on transient failures
- **Consultation Tracking:** Link audio clips to consultations

### Quick Start

```bash
# 1. Navigate to live transcription page
# http://localhost:5000/live-transcription

# 2. Click "Start Recording"

# 3. Speak into microphone

# 4. See real-time transcript

# 5. Click "Stop Recording"
```

---

## 3. Prescription Workflow

### Overview

Complete prescription lifecycle management with state machine, section approval, and soft delete.

### Implementation Status: ✅ Complete

**Components:**
- `services/prescription_service.py` - Core workflow logic
- `routes/prescription_routes.py` - API endpoints
- `templates/prescription_finalize.html` - Finalization UI
- `templates/prescriptions_list.html` - List view
- `templates/prescription_detail.html` - Detail view

### State Machine

```
Draft → InProgress → Finalized
  ↓         ↓           ↓
Deleted ← Deleted ← Deleted
         (30-day retention)
```

**State Descriptions:**

**Draft:**
- Initial creation
- Basic patient information
- No AI content yet
- Editable

**InProgress:**
- AI extraction complete
- Sections populated from Bedrock
- Section-by-section approval required
- Editable (rejected sections only)

**Finalized:**
- All required sections approved
- Immutable (read-only)
- PDF generation enabled
- Audit trail locked

**Deleted:**
- Soft deleted
- 30-day retention
- Restorable by creator
- Automatic cleanup after 30 days

### Section Approval Workflow

1. **Load AI Content:** Transition Draft → InProgress
2. **Review Sections:** Each section has status (Pending/Approved/Rejected)
3. **Approve:** Lock section content
4. **Reject:** Enable inline editing
5. **Edit:** Update content, returns to Pending
6. **Finalize:** When all required sections approved

### API Endpoints

```bash
# Create prescription (Draft)
POST /api/v1/prescriptions
{"patient_name": "John Doe", "hospital_id": "hosp_123"}

# Transition to InProgress
POST /api/v1/prescriptions/:id/transition-to-in-progress
{"transcript": "..."}

# Approve section
POST /api/v1/prescriptions/:id/sections/:key/approve

# Reject section
POST /api/v1/prescriptions/:id/sections/:key/reject

# Update section
PUT /api/v1/prescriptions/:id/sections/:key
{"content": "Updated content"}

# Finalize
POST /api/v1/prescriptions/:id/finalize

# Generate PDF
POST /api/v1/prescriptions/:id/pdf

# Soft delete
DELETE /api/v1/prescriptions/:id

# Restore
POST /api/v1/prescriptions/:id/restore
```

### Features

- **State Validation:** Enforces valid state transitions
- **Approval Gating:** Cannot finalize without all approvals
- **Audit Trail:** Tracks who did what and when
- **Soft Delete:** 30-day recovery window
- **Automatic Cleanup:** Scheduled deletion after retention period
- **PDF Generation:** On-demand with hospital branding

---

## 4. Hospital Management

### Overview

Multi-tenant hospital management with custom configurations, doctor management, and role-based access.

### Implementation Status: ✅ Complete

**Components:**
- `routes/hospital_routes.py` - API endpoints
- `templates/hospital_settings.html` - Settings UI
- `templates/hospitals_list.html` - Hospital list (DeveloperAdmin)
- `migrations/006_create_hospitals_table.sql` - Database schema

### Database Schema

```sql
CREATE TABLE hospitals (
    hospital_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    phone VARCHAR(20),
    email VARCHAR(255),
    logo_url TEXT,
    registration_number VARCHAR(100),
    website VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE doctors (
    doctor_id VARCHAR(255) PRIMARY KEY,
    hospital_id VARCHAR(64) REFERENCES hospitals(hospital_id),
    name VARCHAR(255) NOT NULL,
    specialty VARCHAR(100),
    qualification VARCHAR(255),
    signature_url TEXT,
    availability TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API Endpoints

```bash
# List hospitals (DeveloperAdmin only)
GET /api/v1/hospitals

# Get hospital details
GET /api/v1/hospitals/:id

# Update hospital
PUT /api/v1/hospitals/:id
{
  "name": "Updated Hospital Name",
  "address": "123 Healthcare St",
  "phone": "+91-1234567890",
  "email": "info@hospital.com",
  "logo_url": "https://...",
  "registration_number": "REG123",
  "website": "https://hospital.com"
}

# List doctors
GET /api/v1/hospitals/:id/doctors

# Add doctor
POST /api/v1/hospitals/:id/doctors
{
  "doctor_id": "doctor@hospital.com",
  "name": "Dr. Smith",
  "specialty": "Cardiology"
}

# Remove doctor
DELETE /api/v1/hospitals/:id/doctors/:doctor_id
```

### Features

- **Multi-Tenant:** Isolated data per hospital
- **Custom Configurations:** Hospital-specific prescription fields
- **Doctor Management:** Add/remove doctors
- **Hospital Branding:** Logo, letterhead, contact info
- **Role-Based Access:** HospitalAdmin manages own hospital only

---

## 5. Role-Based Access Control

### Overview

Three-tier role system with fine-grained permissions and SQL-level filtering.

### Implementation Status: ✅ Complete

**Components:**
- `services/rbac_service.py` - Permission checking
- `decorators/auth_decorators.py` - Route protection
- `migrations/008_create_user_roles_table.sql` - Database schema

### Roles

**Doctor:**
- View/edit own prescriptions
- Create prescriptions
- Finalize own prescriptions
- Soft delete/restore own prescriptions

**Hospital Admin:**
- All Doctor capabilities
- View hospital-wide prescriptions
- Manage hospital settings
- Manage doctors in hospital

**Developer Admin:**
- Cross-hospital access
- View all prescriptions
- Hospital CRUD operations
- CloudWatch logs viewer
- System monitoring

### Database Schema

```sql
CREATE TABLE user_roles (
    user_id VARCHAR(255) PRIMARY KEY,
    role VARCHAR(50) NOT NULL CHECK (role IN ('Doctor', 'HospitalAdmin', 'DeveloperAdmin')),
    hospital_id VARCHAR(64) REFERENCES hospitals(hospital_id),
    approval_status VARCHAR(50) DEFAULT 'Pending' CHECK (approval_status IN ('Pending', 'Approved', 'Rejected')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Permission Checking

```python
from services.rbac_service import RBACService

rbac = RBACService(database_manager)

# Check if user can view prescription
can_view = rbac.can_view_prescription(user_id, prescription_id)

# Check if user can edit prescription
can_edit = rbac.can_edit_prescription(user_id, prescription_id)

# Check if user can finalize prescription
can_finalize = rbac.can_finalize_prescription(user_id, prescription_id)

# Get user role
role = rbac.get_user_role(user_id)

# Filter prescriptions by role
prescriptions = rbac.filter_prescriptions_by_role(user_id, all_prescriptions)
```

### Route Protection

```python
from decorators.auth_decorators import require_role

@app.route('/api/v1/hospitals')
@login_required
@require_role('DeveloperAdmin')
def list_hospitals():
    # Only DeveloperAdmin can access
    pass

@app.route('/api/v1/hospitals/<hospital_id>')
@login_required
@require_role('HospitalAdmin', 'DeveloperAdmin')
def get_hospital(hospital_id):
    # HospitalAdmin and DeveloperAdmin can access
    pass
```

### Features

- **SQL-Level Filtering:** Prescriptions filtered in database queries
- **Route Protection:** Decorators enforce role requirements
- **Permission Checking:** Granular permission validation
- **Approval Workflow:** Hospital admin approves new doctors
- **Audit Trail:** Role changes logged

---

## 6. CloudWatch Logs Viewer

### Overview

In-app CloudWatch logs viewer for system monitoring and debugging (DeveloperAdmin only).

### Implementation Status: ✅ Complete

**Components:**
- `services/cloudwatch_service.py` - CloudWatch API integration
- `routes/hospital_routes.py` - Logs endpoint
- `templates/logs_viewer.html` - UI
- `static/js/logs_viewer.js` - Frontend logic

### How It Works

```
Frontend Request
    ↓
Flask API (/api/v1/logs)
    ↓
CloudWatch Logs API
    ↓
Filter & Format Logs
    ↓
Return to Frontend
```

### API Endpoint

```bash
# Get logs
GET /api/v1/logs?start_time=<timestamp>&end_time=<timestamp>&filter_pattern=<pattern>&limit=100

# Response
{
  "success": true,
  "logs": [
    {
      "timestamp": "2026-03-08T10:30:45.123Z",
      "message": "INFO: Prescription created successfully",
      "stream": "ecs/seva-arogya/task-123"
    }
  ],
  "next_token": "..."
}
```

### Features

- **Date Range Filter:** Select start and end time
- **Search Filter:** Text search in log messages
- **Auto-Refresh:** Toggle 30-second auto-refresh
- **Pagination:** Load more logs
- **Log Level Highlighting:** Color-coded ERROR, WARNING, INFO
- **Stream Filtering:** Filter by log stream
- **Export:** Download logs as text file

### UI Features

```javascript
// Date range picker
<input type="datetime-local" id="start-time">
<input type="datetime-local" id="end-time">

// Search filter
<input type="text" placeholder="Search logs..." id="search-filter">

// Auto-refresh toggle
<button id="auto-refresh-toggle">Auto-Refresh: OFF</button>

// Log entries
<div class="log-entry error">
  <span class="timestamp">2026-03-08 10:30:45</span>
  <span class="level">ERROR</span>
  <span class="message">Connection timeout</span>
</div>
```

### IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogStreams",
        "logs:GetLogEvents",
        "logs:FilterLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/ecs/seva-arogya:*"
    }
  ]
}
```

---

## 7. PDF Generation

### Overview

Dynamic PDF generation with hospital branding, multi-language support, and S3 storage.

### Implementation Status: ✅ Complete

**Components:**
- `services/pdf_generator.py` - PDF rendering with ReportLab
- `services/lambda_pdf_service.py` - Lambda integration (optional)
- `lambda/prescription_pdf_generator/` - Lambda function
- `routes/prescription_routes.py` - PDF endpoint

### How It Works

**Option A: Lambda (Scalable)**
```
API Request
    ↓
Lambda Invoke
    ↓
Fetch Prescription + Hospital Data
    ↓
Render PDF (ReportLab)
    ↓
Upload to S3
    ↓
Return Presigned URL (1-hour expiry)
```

**Option B: In-Process (Fallback)**
```
API Request
    ↓
Fetch Prescription + Hospital Data
    ↓
Render PDF (ReportLab)
    ↓
Upload to S3
    ↓
Return Presigned URL
```

### PDF Layout

```
┌─────────────────────────────────────┐
│ Hospital Logo    Hospital Name      │
│ Address, Phone, Email               │
├─────────────────────────────────────┤
│ Date: 2026-03-08                    │
│                                     │
│ Patient Information                 │
│ Name: John Doe                      │
│ Age: 45  Sex: Male  Weight: 75kg   │
│                                     │
│ Vitals                              │
│ BP: 120/80  HR: 72  Temp: 98.6°F   │
│                                     │
│ Diagnosis                           │
│ Acute bronchitis                    │
│                                     │
│ Medications                         │
│ ┌─────────────────────────────────┐ │
│ │ Azithromycin 500mg              │ │
│ │ Once daily for 5 days           │ │
│ ├─────────────────────────────────┤ │
│ │ Paracetamol 650mg               │ │
│ │ Three times daily for 3 days    │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Clinical Notes                      │
│ Rest, drink fluids, follow up if... │
│                                     │
│ ─────────────────────────────────── │
│ Dr. Signature                       │
│ Dr. Name, Specialty                 │
│ Registration No: REG123             │
└─────────────────────────────────────┘
```

### API Endpoint

```bash
# Generate PDF
POST /api/v1/prescriptions/:id/pdf

# Response
{
  "success": true,
  "pdf_url": "https://s3.amazonaws.com/seva-arogya-pdf/prescriptions/123.pdf?...",
  "expires_in": 3600
}
```

### Features

- **Dynamic Sections:** Renders only existing sections
- **Hospital Branding:** Logo, letterhead, contact info
- **Multi-Language:** English and Hindi support
- **Professional Layout:** A4 format, multi-page support
- **Presigned URLs:** Secure, time-limited access
- **S3 Storage:** Durable, scalable storage
- **Lambda Option:** Offload generation for scalability

### Configuration

```bash
# Enable Lambda PDF generation
ENABLE_PRESCRIPTION_PDF_LAMBDA=true
PRESCRIPTION_PDF_LAMBDA_NAME=seva-arogya-pdf-generator

# PDF settings
PDF_GENERATION_TIMEOUT=30
PDF_MAX_FILE_SIZE_MB=10
```

---

## 8. Soft Delete & Cleanup

### Overview

Soft delete with 30-day retention and automatic cleanup scheduler.

### Implementation Status: ✅ Complete

**Components:**
- `services/cleanup_scheduler.py` - APScheduler-based cleanup
- `services/prescription_service.py` - Soft delete logic

### How It Works

```
Soft Delete
    ↓
state = 'Deleted'
deleted_at = now
deleted_by = user_id
pre_deleted_state = previous_state
    ↓
30-Day Retention
    ↓
Cleanup Scheduler (runs daily)
    ↓
Permanent Deletion
    ↓
Delete from database
Delete from S3 (audio, PDFs)
```

### Cleanup Scheduler

```python
from services.cleanup_scheduler import CleanupScheduler

# Initialize
scheduler = CleanupScheduler(
    database_manager,
    storage_manager,
    retention_days=30
)

# Start scheduler
scheduler.start()

# Runs daily at 2:00 AM
# Deletes prescriptions where:
#   state = 'Deleted' AND
#   deleted_at < now - 30 days
```

### API Endpoints

```bash
# Soft delete
DELETE /api/v1/prescriptions/:id

# Response
{
  "success": true,
  "message": "Prescription deleted successfully",
  "can_restore_until": "2026-04-07T10:30:00Z"
}

# Restore
POST /api/v1/prescriptions/:id/restore

# Response
{
  "success": true,
  "message": "Prescription restored successfully",
  "state": "Draft"
}
```

### Features

- **Soft Delete:** Preserves data for 30 days
- **Restore Capability:** Creator can restore within window
- **Automatic Cleanup:** Daily scheduled task
- **Cascading Deletion:** Removes associated S3 objects
- **Audit Trail:** Tracks deletion and restoration

### Configuration

```bash
# Enable cleanup scheduler
CLEANUP_SCHEDULE_ENABLED=true

# Retention period (days)
CLEANUP_RETENTION_DAYS=30
```

---

## 9. Recent Consultations

### Overview

Display recent consultations on home page with quick access.

### Implementation Status: ✅ Complete

**Components:**
- `templates/home.html` - Home page with consultations
- `static/js/home.js` - Frontend logic
- `routes/prescription_routes.py` - API endpoint

### API Endpoint

```bash
# Get recent consultations
GET /api/v1/consultations/recent?limit=5

# Response
{
  "success": true,
  "consultations": [
    {
      "consultation_id": "cons_123",
      "patient_name": "John Doe",
      "status": "COMPLETED",
      "created_at": "2026-03-08T10:00:00Z",
      "prescription_id": "123"
    }
  ]
}
```

### Features

- **Quick Access:** Click to open consultation
- **Status Indicators:** Visual status badges
- **Recent First:** Sorted by creation time
- **Pagination:** Load more consultations
- **Search Integration:** Search from home page

---

## 10. Feature Flags

### Configuration

```bash
# Prescription workflow
ENABLE_PRESCRIPTION_WORKFLOW=true

# CloudWatch logs viewer
ENABLE_CLOUDWATCH_LOGS_VIEWER=true

# Cleanup scheduler
CLEANUP_SCHEDULE_ENABLED=true

# Lambda PDF generation
ENABLE_PRESCRIPTION_PDF_LAMBDA=true

# Comprehend Medical
ENABLE_COMPREHEND_MEDICAL=true
```

### Usage

```python
import os

# Check feature flag
if os.getenv('ENABLE_PRESCRIPTION_WORKFLOW', 'false').lower() == 'true':
    # Enable prescription workflow
    pass
```

---

## 11. Performance Metrics

### Actual Performance

| Feature | Target | Actual |
|---------|--------|--------|
| Transcription | < 2s | ~1.5s |
| AI Extraction | < 3s | ~2.5s |
| PDF Generation | < 5s | ~3s |
| Section Approval | < 300ms | ~200ms |
| State Transition | < 500ms | ~350ms |

### Optimization

- **Database:** Connection pooling, indexes
- **API:** Async processing where possible
- **PDF:** Lambda offloading for scalability
- **Caching:** Hospital configurations cached
- **CDN:** Static assets via CloudFront

---

## 12. Known Limitations

1. **Bedrock Confidence:** Bedrock doesn't provide per-field confidence (using 1.0)
2. **Configuration Hot-Reload:** Requires cache invalidation
3. **Concurrent Transcriptions:** Limited to 10 simultaneous jobs
4. **PDF Size:** Max 10MB per PDF
5. **Audio Format:** WAV, MP3, FLAC, MP4 only

---

## 13. Future Enhancements

### Phase 2 (Q2 2026)
- Drug interaction checking
- Allergy alerts
- Lab result integration
- E-prescription delivery

### Phase 3 (Q3 2026)
- Mobile app (iOS/Android)
- Offline mode
- Voice commands
- Advanced analytics

### Phase 4 (Q4 2026)
- Clinical decision support
- EHR integration
- Predictive analytics
- Treatment recommendations

---

**Feature Documentation Version:** 2.0  
**Last Updated:** March 8, 2026
