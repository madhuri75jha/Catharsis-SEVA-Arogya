# SEVA Arogya - System Design Document

> **📊 Visual Diagrams**: For comprehensive visual representations including architecture diagrams, data flow diagrams, sequence diagrams, and more, please refer to [diagrams.md](diagrams.md).

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Component Design](#4-component-design)
5. [Data Architecture](#5-data-architecture)
6. [API Design](#6-api-design)
7. [Security Architecture](#7-security-architecture)
8. [Infrastructure Design](#8-infrastructure-design)
9. [Integration Design](#9-integration-design)
10. [Deployment Strategy](#10-deployment-strategy)

---

## 1. Executive Summary

### 1.1 System Overview

SEVA Arogya is a cloud-native, voice-enabled clinical prescription system built on AWS infrastructure. The system leverages AI/ML services for speech recognition and natural language processing to transform doctor-patient consultations into structured, professional prescriptions.

### 1.2 Design Principles

**Modularity**: Loosely coupled components for independent scaling and updates
**Scalability**: Horizontal scaling capability from 50 to 500+ concurrent users
**Security**: Defense-in-depth with encryption, authentication, and audit logging
**Reliability**: 99.5% uptime with multi-AZ deployment and graceful degradation
**Performance**: Sub-2-second transcription and sub-300ms UI response times
**Maintainability**: Clear separation of concerns and comprehensive documentation

### 1.3 Architecture Style

- **Frontend**: Single-Page Application (SPA) with React
- **Backend**: RESTful API with microservices-oriented design
- **Infrastructure**: Serverless containers (AWS Fargate)
- **Data**: Relational database with document storage
- **Integration**: Event-driven with synchronous API calls

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────┐
│   Doctor    │
│  (Browser)  │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────────────────────────────────┐
│         Presentation Layer              │
│  React SPA + State Management           │
└──────┬──────────────────────────────────┘
       │ REST API (JWT)
       ▼
┌─────────────────────────────────────────┐
│      Application Load Balancer          │
│  SSL Termination + Health Checks        │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│        Application Layer                │
│  Flask API (ECS Fargate)                │
│  - Auth Service                         │
│  - Transcription Service                │
│  - NLP Service                          │
│  - Suggestion Engine                    │
│  - PDF Generator                        │
└──────┬──────────────────────────────────┘
       │
       ├──────────────┬──────────────┐
       ▼              ▼              ▼
┌──────────┐   ┌──────────┐   ┌──────────┐
│ AWS AI   │   │   RDS    │   │   S3     │
│ Services │   │PostgreSQL│   │  PDFs    │
└──────────┘   └──────────┘   └──────────┘
```

See [diagrams.md](diagrams.md) for detailed architecture diagrams.


### 2.2 Architectural Layers

#### 2.2.1 Presentation Layer (Frontend)
- **Technology**: React 18+ with TypeScript
- **Responsibilities**:
  - User interface rendering
  - Voice recording and audio capture
  - State management (Redux/Context)
  - API communication
  - Client-side validation
  - PDF preview and download

#### 2.2.2 API Gateway Layer
- **Technology**: AWS Application Load Balancer
- **Responsibilities**:
  - SSL/TLS termination
  - Request routing
  - Health checking
  - Load distribution
  - DDoS protection

#### 2.2.3 Application Layer (Backend)
- **Technology**: Flask (Python) on ECS Fargate
- **Responsibilities**:
  - Business logic execution
  - Authentication and authorization
  - Request validation
  - Service orchestration
  - Error handling
  - Logging and monitoring

#### 2.2.4 Data Layer
- **Technologies**: AWS RDS (PostgreSQL), AWS S3
- **Responsibilities**:
  - Persistent data storage
  - Data integrity and consistency
  - Backup and recovery
  - Query optimization

#### 2.2.5 Integration Layer
- **Technologies**: AWS SDK (Boto3), REST APIs
- **Responsibilities**:
  - External service integration
  - API rate limiting
  - Retry logic
  - Circuit breaking

---

## 3. Technology Stack

### 3.1 Frontend Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Framework | React 18+ | Component-based, large ecosystem, excellent performance |
| Language | TypeScript | Type safety, better IDE support, fewer runtime errors |
| State Management | Redux Toolkit | Predictable state, dev tools, middleware support |
| HTTP Client | Axios | Interceptors, automatic transforms, better error handling |
| UI Framework | Material-UI | Professional components, accessibility, customizable |
| Build Tool | Vite | Fast builds, HMR, modern tooling |
| Testing | Jest + React Testing Library | Industry standard, good documentation |

### 3.2 Backend Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Framework | Flask 2.3+ | Lightweight, flexible, Python ecosystem |
| Language | Python 3.11+ | Rich libraries, AWS SDK support, readable |
| WSGI Server | Gunicorn | Production-ready, worker management, performance |
| ORM | SQLAlchemy | Database abstraction, migration support, query builder |
| Validation | Marshmallow | Schema validation, serialization, deserialization |
| Testing | Pytest | Fixtures, parametrization, extensive plugins |
| Linting | Black + Flake8 | Code consistency, PEP 8 compliance |

### 3.3 AWS Services

| Service | Purpose | Key Features Used |
|---------|---------|-------------------|
| ECS Fargate | Container hosting | Serverless, auto-scaling, no server management |
| RDS PostgreSQL | Relational database | Multi-AZ, automated backups, encryption |
| S3 | Object storage | PDF storage, static hosting, versioning |
| Cognito | Authentication | User pools, JWT tokens, MFA support |
| Transcribe Medical | Speech-to-text | Medical vocabulary, Indian accent support |
| Comprehend Medical | NLP | Entity extraction, medical ontology |
| Translate | Translation | Hindi support, custom terminology |
| CloudWatch | Monitoring | Logs, metrics, alarms, dashboards |
| Secrets Manager | Secret storage | Rotation, encryption, IAM integration |
| ALB | Load balancing | HTTPS, health checks, path routing |
| ECR | Container registry | Docker image storage, vulnerability scanning |
| X-Ray | Tracing | Request tracing, performance analysis |


### 3.4 Development & Operations

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Version Control | Git + GitHub | Source code management |
| CI/CD | GitHub Actions | Automated testing and deployment |
| Containerization | Docker | Application packaging |
| IaC | Terraform | Infrastructure provisioning |
| API Documentation | OpenAPI/Swagger | API specification and testing |
| Monitoring | CloudWatch + X-Ray | Application monitoring and tracing |

---

## 4. Component Design

### 4.1 Frontend Components

#### 4.1.1 Component Hierarchy

```
App
├── AuthProvider (Context)
├── Router
│   ├── LoginPage
│   ├── RegisterPage
│   ├── DashboardPage
│   │   ├── Header
│   │   ├── VoiceRecorder
│   │   ├── PrescriptionForm
│   │   │   ├── PatientInfo
│   │   │   ├── SymptomsSection
│   │   │   ├── DiagnosisSection
│   │   │   ├── MedicationsSection
│   │   │   │   └── MedicationItem
│   │   │   └── InstructionsSection
│   │   ├── SuggestionPanel
│   │   └── PrescriptionPreview
│   ├── ProfilePage
│   └── HistoryPage
└── ErrorBoundary
```

#### 4.1.2 Key Components

**VoiceRecorder Component**
- Manages microphone access
- Records audio using MediaRecorder API
- Displays recording status and waveform
- Sends audio to backend API
- Handles recording errors

**PrescriptionForm Component**
- Manages prescription state
- Displays structured fields
- Handles user edits
- Validates input
- Triggers finalization

**SuggestionPanel Component**
- Displays medication suggestions
- Allows one-click acceptance
- Shows confidence scores
- Dismissible interface

### 4.2 Backend Services

#### 4.2.1 Service Architecture

```
Flask Application
├── API Layer (Routes/Controllers)
│   ├── auth_routes.py
│   ├── transcription_routes.py
│   ├── prescription_routes.py
│   └── profile_routes.py
├── Service Layer
│   ├── auth_service.py
│   ├── transcription_service.py
│   ├── nlp_service.py
│   ├── suggestion_service.py
│   ├── pdf_service.py
│   └── translation_service.py
├── Data Access Layer
│   ├── models.py
│   ├── repositories.py
│   └── database.py
├── Middleware
│   ├── auth_middleware.py
│   ├── error_handler.py
│   └── cors_middleware.py
└── Utils
    ├── validators.py
    ├── helpers.py
    └── constants.py
```

#### 4.2.2 Service Descriptions

**Authentication Service**
- Integrates with AWS Cognito
- Validates JWT tokens
- Manages user sessions
- Handles token refresh

**Transcription Service**
- Interfaces with AWS Transcribe Medical
- Manages audio upload
- Handles streaming/batch transcription
- Returns formatted text with confidence scores

**NLP Service**
- Calls AWS Comprehend Medical
- Extracts medical entities
- Maps entities to prescription fields
- Handles entity relationships

**Suggestion Engine**
- Queries doctor's prescription history
- Applies rule-based logic
- Ranks suggestions by relevance
- Learns from doctor preferences

**PDF Service**
- Generates prescription PDFs
- Applies doctor's template
- Handles multi-language rendering
- Uploads to S3

**Translation Service**
- Interfaces with AWS Translate
- Manages custom terminology
- Handles batch translation
- Preserves medical terms


---

## 5. Data Architecture

### 5.1 Database Schema

See [diagrams.md](diagrams.md) for the complete database schema diagram.

#### 5.1.1 Core Tables

**doctors**
```sql
CREATE TABLE doctors (
    doctor_id SERIAL PRIMARY KEY,
    cognito_sub VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    clinic_name VARCHAR(255),
    qualifications TEXT,
    preferred_language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**prescriptions**
```sql
CREATE TABLE prescriptions (
    prescription_id SERIAL PRIMARY KEY,
    doctor_id INTEGER REFERENCES doctors(doctor_id),
    patient_name VARCHAR(255),
    patient_age INTEGER,
    patient_gender VARCHAR(10),
    symptoms TEXT,
    vitals TEXT,
    diagnosis TEXT,
    instructions TEXT,
    language VARCHAR(10) DEFAULT 'en',
    pdf_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_doctor_date (doctor_id, created_at)
);
```

**prescription_medications**
```sql
CREATE TABLE prescription_medications (
    med_id SERIAL PRIMARY KEY,
    prescription_id INTEGER REFERENCES prescriptions(prescription_id) ON DELETE CASCADE,
    medication_name VARCHAR(255) NOT NULL,
    dosage VARCHAR(100),
    frequency VARCHAR(100),
    duration VARCHAR(100),
    instructions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**medications_master**
```sql
CREATE TABLE medications_master (
    medication_id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    generic_name VARCHAR(255),
    category VARCHAR(100),
    common_dosages TEXT,
    common_frequency TEXT,
    typical_duration VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**audit_logs**
```sql
CREATE TABLE audit_logs (
    log_id SERIAL PRIMARY KEY,
    doctor_id INTEGER REFERENCES doctors(doctor_id),
    action VARCHAR(100) NOT NULL,
    details TEXT,
    ip_address VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_doctor_timestamp (doctor_id, timestamp)
);
```

### 5.2 Data Flow

See [diagrams.md](diagrams.md) for detailed data flow diagrams.

#### 5.2.1 Prescription Creation Flow

1. **Voice Input** → Audio bytes
2. **Transcription** → Raw text
3. **NLP Processing** → Structured entities
4. **Suggestion Generation** → Medication recommendations
5. **User Review** → Edited prescription data
6. **Finalization** → Database record + PDF
7. **Storage** → RDS + S3

#### 5.2.2 Data Retention

- **Prescriptions**: Indefinite (legal requirement)
- **Audit Logs**: 7 years
- **Session Tokens**: 1 hour (access), 30 days (refresh)
- **PDF Files**: Indefinite (with lifecycle policies)

### 5.3 Data Security

**Encryption at Rest**:
- RDS: AES-256 encryption enabled
- S3: Server-side encryption (SSE-S3)
- Secrets Manager: KMS encryption

**Encryption in Transit**:
- TLS 1.2+ for all connections
- HTTPS only (enforced by ALB)
- SSL for database connections

**Data Access Control**:
- Row-level security (doctor_id filtering)
- IAM roles for service access
- Least privilege principle

---

## 6. API Design

### 6.1 API Principles

- RESTful design
- JSON request/response format
- JWT authentication
- Versioned endpoints (/api/v1/)
- Consistent error responses
- Rate limiting

### 6.2 Authentication Endpoints

**POST /api/v1/auth/register**
```json
Request:
{
  "name": "Dr. Sharma",
  "email": "sharma@clinic.com",
  "password": "SecurePass123!",
  "phone": "+919876543210",
  "clinic_name": "Sharma Clinic"
}

Response: 201 Created
{
  "message": "Registration successful",
  "user_id": "123",
  "email": "sharma@clinic.com"
}
```

**POST /api/v1/auth/login**
```json
Request:
{
  "email": "sharma@clinic.com",
  "password": "SecurePass123!"
}

Response: 200 OK
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

**POST /api/v1/auth/refresh**
```json
Request:
{
  "refresh_token": "eyJhbGc..."
}

Response: 200 OK
{
  "access_token": "eyJhbGc...",
  "expires_in": 3600
}
```


### 6.3 Transcription Endpoints

**POST /api/v1/transcribe**
```json
Request: multipart/form-data
- audio: <audio file>
- format: "wav"
- language: "en-IN"

Response: 200 OK
{
  "transcript": "Patient has fever for 3 days...",
  "confidence": 0.95,
  "entities": [
    {
      "type": "SYMPTOM",
      "text": "fever",
      "confidence": 0.98
    },
    {
      "type": "DURATION",
      "text": "3 days",
      "confidence": 0.96
    }
  ],
  "structured_data": {
    "symptoms": ["fever (3 days)"],
    "vitals": [],
    "diagnosis": null,
    "medications": []
  },
  "suggestions": {
    "medications": [
      {
        "name": "Paracetamol",
        "dosage": "500mg",
        "frequency": "Twice daily",
        "confidence": 0.85
      }
    ]
  }
}
```

### 6.4 Prescription Endpoints

**POST /api/v1/prescriptions**
```json
Request:
{
  "patient_name": "Rajesh Kumar",
  "patient_age": 45,
  "patient_gender": "Male",
  "symptoms": "Fever, headache",
  "vitals": "BP: 120/80, Temp: 101F",
  "diagnosis": "Viral fever",
  "medications": [
    {
      "name": "Paracetamol",
      "dosage": "500mg",
      "frequency": "Twice daily",
      "duration": "3 days",
      "instructions": "Take after food"
    }
  ],
  "instructions": "Rest and hydration",
  "language": "en"
}

Response: 201 Created
{
  "prescription_id": 456,
  "pdf_url": "https://s3.../prescriptions/456.pdf",
  "created_at": "2026-02-11T10:30:00Z"
}
```

**GET /api/v1/prescriptions**
```json
Query Parameters:
- page: 1
- limit: 20
- from_date: "2026-02-01"
- to_date: "2026-02-11"

Response: 200 OK
{
  "prescriptions": [
    {
      "prescription_id": 456,
      "patient_name": "Rajesh Kumar",
      "diagnosis": "Viral fever",
      "created_at": "2026-02-11T10:30:00Z",
      "pdf_url": "https://s3.../prescriptions/456.pdf"
    }
  ],
  "total": 45,
  "page": 1,
  "pages": 3
}
```

**GET /api/v1/prescriptions/{id}**
```json
Response: 200 OK
{
  "prescription_id": 456,
  "patient_name": "Rajesh Kumar",
  "patient_age": 45,
  "symptoms": "Fever, headache",
  "diagnosis": "Viral fever",
  "medications": [...],
  "pdf_url": "https://s3.../prescriptions/456.pdf",
  "created_at": "2026-02-11T10:30:00Z"
}
```

### 6.5 Profile Endpoints

**GET /api/v1/profile**
```json
Response: 200 OK
{
  "doctor_id": 123,
  "name": "Dr. Sharma",
  "email": "sharma@clinic.com",
  "clinic_name": "Sharma Clinic",
  "qualifications": "MBBS, MD",
  "preferred_language": "en"
}
```

**PUT /api/v1/profile**
```json
Request:
{
  "clinic_name": "Sharma Multi-Specialty Clinic",
  "preferred_language": "hi"
}

Response: 200 OK
{
  "message": "Profile updated successfully"
}
```

### 6.6 Error Responses

**Standard Error Format**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "patient_age",
        "message": "Must be a positive integer"
      }
    ]
  }
}
```

**HTTP Status Codes**
- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 429: Too Many Requests
- 500: Internal Server Error
- 503: Service Unavailable


---

## 7. Security Architecture

See [diagrams.md](diagrams.md) for detailed security architecture diagrams.

### 7.1 Authentication & Authorization

#### 7.1.1 Authentication Flow

1. User submits credentials to Cognito
2. Cognito validates and returns JWT tokens
3. Frontend stores tokens securely
4. All API requests include JWT in Authorization header
5. Backend validates JWT signature and expiration
6. Backend extracts user identity from token
7. Backend authorizes request based on user identity

#### 7.1.2 JWT Token Structure

**Access Token** (1 hour expiry):
```json
{
  "sub": "cognito-user-id",
  "email": "sharma@clinic.com",
  "cognito:groups": ["doctors"],
  "exp": 1707649800,
  "iat": 1707646200
}
```

**Refresh Token** (30 days expiry):
- Used to obtain new access tokens
- Stored securely (httpOnly cookie or secure storage)
- Revocable via Cognito

#### 7.1.3 Authorization Rules

- Doctors can only access their own data
- All endpoints require authentication (except /auth/*)
- Row-level filtering by doctor_id
- No admin roles in MVP (future enhancement)

### 7.2 Network Security

#### 7.2.1 VPC Architecture

**Public Subnet**:
- Application Load Balancer
- NAT Gateway
- Bastion host (optional, for debugging)

**Private Subnet**:
- ECS Fargate tasks
- RDS database
- No direct internet access

#### 7.2.2 Security Groups

**ALB Security Group**:
- Inbound: 443 from 0.0.0.0/0
- Outbound: 5000 to ECS-SG

**ECS Security Group**:
- Inbound: 5000 from ALB-SG
- Outbound: 5432 to RDS-SG
- Outbound: 443 to 0.0.0.0/0 (AWS APIs)

**RDS Security Group**:
- Inbound: 5432 from ECS-SG
- Outbound: None

### 7.3 Data Security

#### 7.3.1 Encryption

**At Rest**:
- RDS: AWS-managed KMS encryption
- S3: SSE-S3 encryption
- EBS: Encrypted volumes
- Secrets Manager: KMS encryption

**In Transit**:
- HTTPS/TLS 1.2+ for all external communication
- SSL for database connections
- Encrypted AWS API calls

#### 7.3.2 Secrets Management

**Stored in AWS Secrets Manager**:
- Database credentials
- JWT signing keys
- API keys (if any)
- Encryption keys

**Access Control**:
- IAM roles for ECS tasks
- Least privilege principle
- Automatic rotation (where supported)

### 7.4 Application Security

#### 7.4.1 Input Validation

- Server-side validation for all inputs
- Marshmallow schemas for request validation
- SQL injection prevention (parameterized queries)
- XSS prevention (output encoding)
- File upload validation (type, size)

#### 7.4.2 Rate Limiting

- 100 requests/minute per user (general)
- 20 transcription requests/minute per user
- 429 status code on limit exceeded
- Exponential backoff recommended

#### 7.4.3 CORS Policy

```python
CORS_ORIGINS = [
    "https://app.seva-arogya.com",
    "https://staging.seva-arogya.com"
]
CORS_METHODS = ["GET", "POST", "PUT", "DELETE"]
CORS_ALLOW_HEADERS = ["Authorization", "Content-Type"]
```

### 7.5 Audit & Compliance

#### 7.5.1 Audit Logging

**Logged Events**:
- User login/logout
- Prescription creation
- Profile updates
- Failed authentication attempts
- API errors

**Log Format**:
```json
{
  "timestamp": "2026-02-11T10:30:00Z",
  "doctor_id": 123,
  "action": "CREATE_PRESCRIPTION",
  "ip_address": "203.0.113.42",
  "user_agent": "Mozilla/5.0...",
  "details": {
    "prescription_id": 456,
    "patient_name": "Rajesh Kumar"
  }
}
```

#### 7.5.2 Compliance Considerations

**DISHA (India)**:
- Data residency in India (ap-south-1)
- Audit trail maintenance
- Consent management (future)
- Data retention policies

**General Best Practices**:
- Encryption at rest and in transit
- Access controls and authentication
- Regular security audits
- Incident response plan

---

## 8. Infrastructure Design

See [diagrams.md](diagrams.md) for detailed AWS infrastructure diagrams.

### 8.1 AWS Resource Architecture

#### 8.1.1 Compute Resources

**ECS Cluster**:
- Name: seva-arogya-cluster
- Launch Type: Fargate
- Region: ap-south-1 (Mumbai)

**Task Definition**:
```yaml
Family: seva-arogya-api
CPU: 512 (0.5 vCPU)
Memory: 1024 MB
Container:
  Name: flask-api
  Image: <account>.dkr.ecr.ap-south-1.amazonaws.com/seva-arogya:latest
  Port: 5000
  Environment:
    - DATABASE_URL: <from Secrets Manager>
    - AWS_REGION: ap-south-1
  Logging:
    Driver: awslogs
    Options:
      awslogs-group: /ecs/seva-arogya
      awslogs-region: ap-south-1
```

**Service Configuration**:
- Desired Count: 2
- Min: 2, Max: 10
- Auto-scaling: Target CPU 70%
- Health Check: /health endpoint
- Deployment: Rolling update


#### 8.1.2 Database Resources

**RDS Instance**:
```yaml
Engine: PostgreSQL 15
Instance Class: db.t3.medium
Storage: 100 GB (gp3)
Multi-AZ: Yes
Backup Retention: 7 days
Encryption: Yes (KMS)
Parameter Group: Custom (connection pooling optimized)
```

**Connection Pooling**:
- SQLAlchemy pool size: 10
- Max overflow: 20
- Pool recycle: 3600 seconds

#### 8.1.3 Storage Resources

**S3 Buckets**:

1. **seva-arogya-prescriptions** (Private)
   - Purpose: PDF storage
   - Versioning: Enabled
   - Encryption: SSE-S3
   - Lifecycle: None (indefinite retention)

2. **seva-arogya-static** (Public Read)
   - Purpose: Frontend static assets
   - Versioning: Enabled
   - CloudFront: Yes
   - Encryption: SSE-S3

#### 8.1.4 Networking Resources

**VPC Configuration**:
```yaml
VPC CIDR: 10.0.0.0/16
Availability Zones: ap-south-1a, ap-south-1b

Public Subnets:
  - 10.0.1.0/24 (AZ-1)
  - 10.0.2.0/24 (AZ-2)

Private Subnets:
  - 10.0.11.0/24 (AZ-1)
  - 10.0.12.0/24 (AZ-2)

NAT Gateway: 1 per AZ
Internet Gateway: 1
```

**Application Load Balancer**:
```yaml
Scheme: Internet-facing
Subnets: Public subnets (both AZs)
Security Group: ALB-SG
Listeners:
  - Port: 443 (HTTPS)
    Certificate: ACM certificate
    Default Action: Forward to ECS target group
Target Group:
  Protocol: HTTP
  Port: 5000
  Health Check: /health
  Deregistration Delay: 30s
```

### 8.2 Monitoring & Observability

#### 8.2.1 CloudWatch Metrics

**Application Metrics**:
- Request count
- Response time (p50, p95, p99)
- Error rate
- Transcription latency
- Database query time

**Infrastructure Metrics**:
- ECS CPU/Memory utilization
- RDS CPU/Memory/Storage
- ALB request count
- ALB target response time

#### 8.2.2 CloudWatch Alarms

**Critical Alarms**:
- ECS CPU > 80% for 5 minutes
- RDS CPU > 80% for 5 minutes
- Error rate > 5% for 5 minutes
- ALB 5xx errors > 10 in 5 minutes
- RDS storage < 10 GB

**Warning Alarms**:
- ECS CPU > 70% for 10 minutes
- Response time p95 > 2 seconds
- Database connections > 80%

#### 8.2.3 Logging Strategy

**Log Groups**:
- /ecs/seva-arogya (Application logs)
- /aws/rds/seva-arogya (Database logs)
- /aws/lambda/seva-arogya-* (Lambda logs, if any)

**Log Retention**:
- Application logs: 30 days
- Database logs: 7 days
- Audit logs: 7 years (in RDS)

**Log Format** (Structured JSON):
```json
{
  "timestamp": "2026-02-11T10:30:00Z",
  "level": "INFO",
  "service": "transcription",
  "trace_id": "abc123",
  "message": "Transcription completed",
  "duration_ms": 1850,
  "doctor_id": 123
}
```

#### 8.2.4 Distributed Tracing

**AWS X-Ray**:
- Trace all API requests
- Track external service calls (Transcribe, Comprehend)
- Identify performance bottlenecks
- Service map visualization

### 8.3 Disaster Recovery

#### 8.3.1 Backup Strategy

**RDS Backups**:
- Automated daily backups (7-day retention)
- Manual snapshots before major changes
- Cross-region backup (future)

**S3 Versioning**:
- Enabled on all buckets
- Accidental deletion protection

#### 8.3.2 Recovery Procedures

**RDS Failure**:
1. Automatic failover to standby (Multi-AZ)
2. RTO: < 2 minutes
3. RPO: 0 (synchronous replication)

**ECS Task Failure**:
1. Automatic task replacement
2. Health check triggers replacement
3. RTO: < 1 minute

**Complete Region Failure**:
1. Manual failover to backup region (future)
2. RTO: 4 hours
3. RPO: 24 hours (daily backups)

---

## 9. Integration Design

### 9.1 AWS Service Integrations

#### 9.1.1 AWS Transcribe Medical

**Integration Pattern**: Synchronous API call

**Implementation**:
```python
import boto3

transcribe = boto3.client('transcribe', region_name='ap-south-1')

def transcribe_audio(audio_bytes, language='en-IN'):
    # Upload to S3 (temporary)
    s3_uri = upload_to_temp_s3(audio_bytes)
    
    # Start transcription job
    job_name = f"transcription-{uuid.uuid4()}"
    transcribe.start_medical_transcription_job(
        MedicalTranscriptionJobName=job_name,
        LanguageCode=language,
        MediaFormat='wav',
        Media={'MediaFileUri': s3_uri},
        OutputBucketName='seva-arogya-temp',
        Specialty='PRIMARYCARE',
        Type='DICTATION'
    )
    
    # Poll for completion
    while True:
        status = transcribe.get_medical_transcription_job(
            MedicalTranscriptionJobName=job_name
        )
        if status['MedicalTranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
            break
        time.sleep(1)
    
    # Retrieve transcript
    transcript_uri = status['MedicalTranscriptionJob']['Transcript']['TranscriptFileUri']
    transcript = download_transcript(transcript_uri)
    
    return transcript
```

**Error Handling**:
- Retry on transient failures (3 attempts)
- Fallback to standard Transcribe if Medical unavailable
- User notification on persistent failures


#### 9.1.2 AWS Comprehend Medical

**Integration Pattern**: Synchronous API call

**Implementation**:
```python
comprehend = boto3.client('comprehendmedical', region_name='ap-south-1')

def extract_entities(text):
    response = comprehend.detect_entities_v2(Text=text)
    
    entities = {
        'medications': [],
        'symptoms': [],
        'dosages': [],
        'diagnoses': []
    }
    
    for entity in response['Entities']:
        category = entity['Category']
        text = entity['Text']
        confidence = entity['Score']
        
        if category == 'MEDICATION':
            entities['medications'].append({
                'name': text,
                'confidence': confidence
            })
        elif category == 'MEDICAL_CONDITION':
            if entity['Type'] == 'DX_NAME':
                entities['diagnoses'].append(text)
            else:
                entities['symptoms'].append(text)
        elif category == 'DOSAGE':
            entities['dosages'].append(text)
    
    return entities
```

#### 9.1.3 AWS Translate

**Integration Pattern**: Batch API call

**Implementation**:
```python
translate = boto3.client('translate', region_name='ap-south-1')

def translate_prescription(prescription_data, target_language='hi'):
    # Fields to translate
    translatable_fields = [
        'symptoms',
        'diagnosis',
        'instructions'
    ]
    
    translated = {}
    
    for field in translatable_fields:
        if prescription_data.get(field):
            response = translate.translate_text(
                Text=prescription_data[field],
                SourceLanguageCode='en',
                TargetLanguageCode=target_language,
                TerminologyNames=['medical-terms']  # Custom terminology
            )
            translated[field] = response['TranslatedText']
    
    # Preserve medication names (don't translate)
    translated['medications'] = prescription_data['medications']
    
    return translated
```

**Custom Terminology**:
```csv
en,hi
twice daily,दिन में दो बार
after food,भोजन के बाद
before food,भोजन से पहले
tablet,गोली
capsule,कैप्सूल
```

### 9.2 Frontend-Backend Integration

#### 9.2.1 API Client Configuration

**Axios Configuration**:
```javascript
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor (add JWT)
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor (handle token refresh)
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try to refresh token
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post('/api/v1/auth/refresh', {
            refresh_token: refreshToken
          });
          localStorage.setItem('access_token', response.data.access_token);
          // Retry original request
          error.config.headers.Authorization = `Bearer ${response.data.access_token}`;
          return axios(error.config);
        } catch (refreshError) {
          // Refresh failed, redirect to login
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);
```

#### 9.2.2 State Management

**Redux Store Structure**:
```javascript
{
  auth: {
    user: { id, name, email },
    isAuthenticated: boolean,
    loading: boolean
  },
  prescription: {
    current: {
      patientInfo: {},
      symptoms: [],
      diagnosis: '',
      medications: [],
      instructions: ''
    },
    suggestions: [],
    loading: boolean,
    error: null
  },
  history: {
    prescriptions: [],
    total: 0,
    page: 1,
    loading: boolean
  }
}
```

---

## 10. Deployment Strategy

### 10.1 Environment Strategy

#### 10.1.1 Environments

**Development**:
- Purpose: Developer testing
- Infrastructure: Minimal (1 ECS task, small RDS)
- Data: Synthetic test data
- Deployment: Manual or on commit to dev branch

**Staging**:
- Purpose: QA and UAT
- Infrastructure: Production-like (2 ECS tasks, medium RDS)
- Data: Anonymized production data
- Deployment: Automatic on merge to staging branch

**Production**:
- Purpose: Live system
- Infrastructure: Full (2-10 ECS tasks, Multi-AZ RDS)
- Data: Real data
- Deployment: Manual approval after staging validation

#### 10.1.2 Configuration Management

**Environment Variables**:
```bash
# Development
DATABASE_URL=postgresql://dev:pass@dev-db:5432/seva_arogya
AWS_REGION=ap-south-1
LOG_LEVEL=DEBUG
ENVIRONMENT=development

# Production
DATABASE_URL=<from Secrets Manager>
AWS_REGION=ap-south-1
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### 10.2 CI/CD Pipeline

#### 10.2.1 GitHub Actions Workflow

**Pipeline Stages**:

1. **Code Quality**
   - Linting (Black, Flake8, ESLint)
   - Type checking (mypy, TypeScript)
   - Security scanning (Bandit, npm audit)

2. **Testing**
   - Unit tests (pytest, Jest)
   - Integration tests
   - Code coverage report (>70% required)

3. **Build**
   - Build Docker image
   - Tag with commit SHA and branch
   - Push to ECR

4. **Deploy to Staging**
   - Update ECS task definition
   - Deploy to staging cluster
   - Run smoke tests

5. **Manual Approval**
   - Review staging deployment
   - Approve for production

6. **Deploy to Production**
   - Blue-green deployment
   - Update ECS service
   - Monitor for errors
   - Automatic rollback on failure


#### 10.2.2 Deployment Configuration

**GitHub Actions Workflow** (.github/workflows/deploy.yml):
```yaml
name: Deploy SEVA Arogya

on:
  push:
    branches: [main, staging, dev]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run linters
        run: |
          black --check .
          flake8 .
      - name: Run tests
        run: pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-south-1
      - name: Login to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin ${{ secrets.ECR_REGISTRY }}
      - name: Build and push
        run: |
          docker build -t seva-arogya:${{ github.sha }} .
          docker tag seva-arogya:${{ github.sha }} ${{ secrets.ECR_REGISTRY }}/seva-arogya:${{ github.sha }}
          docker push ${{ secrets.ECR_REGISTRY }}/seva-arogya:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster seva-arogya-cluster \
            --service seva-arogya-api \
            --force-new-deployment \
            --region ap-south-1
```

### 10.3 Database Migrations

#### 10.3.1 Migration Strategy

**Tool**: Alembic (SQLAlchemy migrations)

**Process**:
1. Developer creates migration script
2. Migration tested in development
3. Migration applied to staging
4. Validation in staging
5. Migration applied to production (during maintenance window)

**Example Migration**:
```python
# alembic/versions/001_create_doctors_table.py
def upgrade():
    op.create_table(
        'doctors',
        sa.Column('doctor_id', sa.Integer(), primary_key=True),
        sa.Column('cognito_sub', sa.String(255), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )

def downgrade():
    op.drop_table('doctors')
```

### 10.4 Rollback Strategy

#### 10.4.1 Application Rollback

**ECS Rollback**:
- Keep previous task definition
- Update service to use previous task definition
- Monitor for stability
- RTO: < 5 minutes

**Automated Rollback Triggers**:
- Error rate > 10% for 5 minutes
- Health check failures > 50%
- Manual trigger via AWS Console

#### 10.4.2 Database Rollback

**Migration Rollback**:
```bash
# Rollback last migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision>
```

**Data Rollback**:
- Restore from RDS snapshot
- Point-in-time recovery
- RTO: 30 minutes
- RPO: 5 minutes (transaction logs)

### 10.5 Monitoring Deployment

#### 10.5.1 Deployment Metrics

**Key Metrics to Monitor**:
- Deployment duration
- Error rate (before vs after)
- Response time (before vs after)
- CPU/Memory utilization
- Database connection count

**Deployment Dashboard**:
- Real-time error rate
- Request count
- Response time percentiles
- Active connections
- Task health status

#### 10.5.2 Post-Deployment Validation

**Smoke Tests**:
1. Health check endpoint responds
2. Login flow works
3. Transcription API responds
4. Prescription creation works
5. PDF generation works

**Automated Tests**:
```bash
# Run smoke tests after deployment
./scripts/smoke-tests.sh production

# Tests include:
# - API health check
# - Authentication flow
# - Sample transcription
# - Sample prescription creation
```

---

## 11. Performance Optimization

### 11.1 Backend Optimization

**Database Query Optimization**:
- Indexes on frequently queried columns
- Connection pooling (10 connections)
- Query result caching (Redis, future)
- Pagination for list endpoints

**API Response Optimization**:
- Gzip compression
- Response caching headers
- Minimal payload size
- Async processing for long operations

**Resource Management**:
- Gunicorn worker count: 4 per container
- Worker timeout: 30 seconds
- Keep-alive connections
- Connection pooling

### 11.2 Frontend Optimization

**Bundle Optimization**:
- Code splitting by route
- Lazy loading components
- Tree shaking
- Minification and compression

**Caching Strategy**:
- Service worker for offline support (future)
- LocalStorage for user preferences
- API response caching (short TTL)

**Performance Targets**:
- First Contentful Paint: < 1.5s
- Time to Interactive: < 3s
- Lighthouse Score: > 90

### 11.3 AWS Service Optimization

**Cost Optimization**:
- Right-size ECS tasks (monitor utilization)
- Use Fargate Spot for non-critical tasks (future)
- S3 Intelligent-Tiering for old PDFs
- RDS Reserved Instances for predictable load

**Performance Optimization**:
- CloudFront CDN for static assets
- Multi-AZ for low latency
- VPC endpoints for AWS services (reduce NAT costs)

---

## 12. Testing Strategy

### 12.1 Testing Pyramid

**Unit Tests** (70%):
- Service layer logic
- Utility functions
- Data transformations
- Validation logic

**Integration Tests** (20%):
- API endpoints
- Database operations
- AWS service mocks
- Authentication flow

**End-to-End Tests** (10%):
- Complete user flows
- Cross-component interactions
- UI automation (Cypress)

### 12.2 Test Coverage Requirements

- Overall: > 70%
- Critical paths: > 90%
- Service layer: > 80%
- API routes: > 75%

---

## 13. Documentation

### 13.1 Technical Documentation

- **API Documentation**: OpenAPI/Swagger spec
- **Database Schema**: ER diagrams, table descriptions
- **Architecture Diagrams**: See [diagrams.md](diagrams.md)
- **Deployment Guide**: Step-by-step deployment instructions
- **Runbook**: Operational procedures, troubleshooting

### 13.2 Developer Documentation

- **Setup Guide**: Local development environment
- **Coding Standards**: Style guide, best practices
- **Contributing Guide**: PR process, code review checklist
- **Architecture Decision Records**: Key design decisions

---

## 14. Future Enhancements

### 14.1 Technical Improvements

- **Microservices**: Split monolith into services
- **Event-Driven**: Use SQS/SNS for async processing
- **Caching Layer**: Redis for session and data caching
- **GraphQL**: Alternative to REST for flexible queries
- **WebSockets**: Real-time transcription streaming

### 14.2 Feature Enhancements

- **Mobile Apps**: Native iOS/Android applications
- **Offline Mode**: PWA with offline capability
- **Voice Commands**: "Next line", "Undo", etc.
- **Templates**: Reusable prescription templates
- **Analytics**: Usage insights and reporting

---

## 15. Appendices

### 15.1 Glossary

See [requirements.md](requirements.md) Section 13 for complete glossary.

### 15.2 References

- [requirements.md](requirements.md) - Detailed requirements
- [diagrams.md](diagrams.md) - Visual diagrams
- [Readme.md](Readme.md) - System overview
- AWS Documentation
- Flask Documentation
- React Documentation

### 15.3 Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 2.0 | 2026-02-11 | Complete redesign with diagrams | System |
| 1.0 | 2026-02-01 | Initial design document | System |

---

**Document Version**: 2.0  
**Last Updated**: 2026-02-11  
**Status**: Approved for Implementation  
**Next Review**: 2026-03-11
