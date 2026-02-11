# SEVA Arogya - System Design Document

**Version**: 2.0 | **Last Updated**: 2026-02-11 | **Status**: Approved for Implementation

---

## 1. Executive Summary

SEVA Arogya is a cloud-native voice-enabled prescription system built on AWS infrastructure. It transforms doctor-patient consultations into structured, professional prescriptions using AI/ML services for speech recognition and natural language processing.

**Design Principles**: Modularity, horizontal scalability (50-500+ users), defense-in-depth security, 99.5% uptime, sub-2-second transcription, and clear separation of concerns.

**Architecture Style**: React SPA frontend, Flask RESTful API backend, serverless containers (AWS Fargate), PostgreSQL database, and event-driven integration.

---

## 2. System Architecture

### 2.1 High-Level Architecture

The system follows a 5-layer architecture:

1. **Presentation Layer**: React 18+ SPA with TypeScript, Redux state management, and Web Audio API for voice capture
2. **API Gateway Layer**: AWS Application Load Balancer handling SSL termination, routing, and health checks
3. **Application Layer**: Flask (Python) on ECS Fargate with auth, transcription, NLP, suggestion engine, and PDF generation services
4. **Data Layer**: AWS RDS (PostgreSQL) for structured data and S3 for PDF storage
5. **Integration Layer**: AWS SDK (Boto3) for external service integration with retry logic and circuit breaking

### 2.2 Key Components

**Frontend Components**:
- VoiceRecorder: Manages microphone access and audio recording
- PrescriptionForm: Handles structured fields and user edits
- SuggestionPanel: Displays medication recommendations
- AuthProvider: Manages JWT tokens and authentication state

**Backend Services**:
- Authentication Service: Cognito integration and JWT validation
- Transcription Service: AWS Transcribe Medical interface
- NLP Service: AWS Comprehend Medical for entity extraction
- Suggestion Engine: Context-aware medication recommendations
- PDF Service: Template-based prescription generation
- Translation Service: AWS Translate for multi-language support

---

## 3. Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React 18+ + TypeScript | Component-based, type safety, large ecosystem |
| Backend | Flask (Python 3.11+) | Lightweight, AWS SDK support, rapid development |
| Database | PostgreSQL 13+ (RDS) | ACID compliance, JSON support, managed service |
| Container | Docker + ECS Fargate | Serverless, auto-scaling, no server management |
| Auth | AWS Cognito | Managed service, JWT tokens, MFA support |
| STT | AWS Transcribe Medical | Medical vocabulary, Indian accent support |
| NLP | AWS Comprehend Medical | Entity extraction, medical ontology |
| Translation | AWS Translate | Hindi support, custom terminology |
| Storage | AWS S3 | PDF storage, static hosting, 99.999999999% durability |
| Monitoring | CloudWatch + X-Ray | Logs, metrics, distributed tracing |

---

## 4. Data Architecture

### 4.1 Database Schema

**Core Tables**:
- `doctors`: User profiles (doctor_id, cognito_sub, name, email, clinic_name, preferred_language)
- `prescriptions`: Prescription records (prescription_id, doctor_id, patient_info, symptoms, diagnosis, instructions, pdf_url)
- `prescription_medications`: Medication details (med_id, prescription_id, medication_name, dosage, frequency, duration)
- `medications_master`: Reference data for suggestions
- `audit_logs`: Security audit trail (log_id, doctor_id, action, timestamp, ip_address)

**Relationships**: doctors (1:N) prescriptions (1:N) prescription_medications

**Indexes**: doctor_id + created_at for fast prescription retrieval

### 4.2 Data Security

- **At Rest**: RDS AES-256 encryption, S3 SSE-S3 encryption
- **In Transit**: TLS 1.2+ for all connections, HTTPS only
- **Access Control**: Row-level filtering by doctor_id, IAM roles for service access

---

## 5. API Design

### 5.1 Core Endpoints

**Authentication**:
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - Login (returns JWT tokens)
- `POST /api/v1/auth/refresh` - Token refresh

**Transcription**:
- `POST /api/v1/transcribe` - Audio transcription (multipart/form-data)
  - Returns: transcript, entities, structured_data, suggestions

**Prescriptions**:
- `POST /api/v1/prescriptions` - Create prescription
  - Input: patient_info, symptoms, diagnosis, medications, language
  - Returns: prescription_id, pdf_url
- `GET /api/v1/prescriptions` - List prescriptions (paginated)
- `GET /api/v1/prescriptions/{id}` - Get specific prescription

**Profile**:
- `GET /api/v1/profile` - Get doctor profile
- `PUT /api/v1/profile` - Update profile settings

### 5.2 API Standards

- RESTful design with JSON format
- JWT authentication (Bearer token)
- Versioned endpoints (/api/v1/)
- Standard HTTP status codes (200, 201, 400, 401, 404, 500)
- Rate limiting: 100 requests/minute general, 20 transcriptions/minute
- CORS enabled for allowed origins

---

## 6. Security Architecture

### 6.1 Authentication Flow

1. User submits credentials to Cognito
2. Cognito validates and returns JWT tokens (access + refresh)
3. Frontend stores tokens securely
4. All API requests include JWT in Authorization header
5. Backend validates JWT signature and expiration
6. Backend extracts user identity and authorizes request

**Token Expiry**: Access token (1 hour), Refresh token (30 days)

### 6.2 Network Security

**VPC Architecture**:
- Public Subnet: ALB, NAT Gateway
- Private Subnet: ECS tasks, RDS database

**Security Groups**:
- ALB-SG: Inbound 443 from internet, Outbound to ECS-SG
- ECS-SG: Inbound 5000 from ALB-SG, Outbound to RDS-SG and internet
- RDS-SG: Inbound 5432 from ECS-SG only

### 6.3 Application Security

- Input validation with Marshmallow schemas
- SQL injection prevention (parameterized queries)
- XSS prevention (output encoding)
- Rate limiting per user
- Audit logging for all actions
- Secrets stored in AWS Secrets Manager

---

## 7. Infrastructure Design

### 7.1 AWS Resources

**Compute**:
- ECS Cluster: seva-arogya-cluster (Fargate)
- Task Definition: 0.5 vCPU, 1GB memory
- Service: 2-10 tasks with auto-scaling (target CPU 70%)

**Database**:
- RDS PostgreSQL 15, db.t3.medium
- Multi-AZ deployment, 100GB storage
- Automated backups (7-day retention)

**Storage**:
- S3 Bucket: seva-arogya-prescriptions (private, encrypted)
- S3 Bucket: seva-arogya-static (public read, CloudFront)

**Networking**:
- VPC: 10.0.0.0/16
- Public Subnets: 10.0.1.0/24, 10.0.2.0/24
- Private Subnets: 10.0.11.0/24, 10.0.12.0/24
- ALB: Internet-facing, HTTPS (443), ACM certificate

### 7.2 Monitoring

**CloudWatch Metrics**: Request count, response time (p50/p95/p99), error rate, CPU/memory utilization

**CloudWatch Alarms**: CPU > 80%, error rate > 5%, RDS storage < 10GB

**X-Ray Tracing**: All API requests, external service calls, performance bottlenecks

**Log Retention**: Application logs (30 days), Database logs (7 days), Audit logs (7 years)

---

## 8. Integration Design

### 8.1 AWS Service Integration

**Transcribe Medical**: Synchronous API call, upload to temp S3, poll for completion, retrieve transcript

**Comprehend Medical**: Synchronous entity extraction, returns medications, symptoms, dosages, diagnoses

**Translate**: Batch translation with custom terminology, preserves medical terms

**Cognito**: JWT token validation using JWKS, automatic token refresh

### 8.2 Error Handling

- Retry on transient failures (3 attempts with exponential backoff)
- Fallback to standard Transcribe if Medical unavailable
- User notification on persistent failures
- Graceful degradation (manual typing if transcription fails)

---

## 9. Deployment Strategy

### 9.1 Environments

- **Development**: 1 ECS task, small RDS, synthetic data
- **Staging**: 2 ECS tasks, medium RDS, anonymized production data
- **Production**: 2-10 ECS tasks, Multi-AZ RDS, real data

### 9.2 CI/CD Pipeline (GitHub Actions)

1. **Code Quality**: Linting (Black, Flake8), type checking, security scanning
2. **Testing**: Unit tests, integration tests, coverage > 70%
3. **Build**: Docker image build and push to ECR
4. **Deploy to Staging**: Update ECS, run smoke tests
5. **Manual Approval**: Review staging deployment
6. **Deploy to Production**: Blue-green deployment, automatic rollback on failure

### 9.3 Database Migrations

- Tool: Alembic (SQLAlchemy migrations)
- Process: Dev → Staging → Production (during maintenance window)
- Rollback: Alembic downgrade or RDS snapshot restore

---

## 10. Performance Optimization

**Backend**: Database query optimization with indexes, connection pooling (10 connections), Gunicorn workers (4 per container)

**Frontend**: Code splitting, lazy loading, tree shaking, minification, service worker (future)

**AWS**: CloudFront CDN for static assets, Multi-AZ for low latency, VPC endpoints for AWS services

**Targets**: First Contentful Paint < 1.5s, Time to Interactive < 3s, Lighthouse Score > 90

---

## 11. Testing Strategy

**Unit Tests (70%)**: Service layer logic, utility functions, validation  
**Integration Tests (20%)**: API endpoints, database operations, AWS service mocks  
**End-to-End Tests (10%)**: Complete user flows, UI automation (Cypress)

**Coverage Requirements**: Overall > 70%, Critical paths > 90%, Service layer > 80%

---

## Document Navigation

For requirements, user stories, acceptance criteria, and visual diagrams, refer to **requirements.md**.

**Version**: 2.0 | **Status**: Approved | **Next Review**: 2026-03-11
