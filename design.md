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

### 6.2 Network & Application Security

**VPC**: Public subnet (ALB, NAT), Private subnet (ECS, RDS)  
**Security Groups**: ALB (443 in) → ECS (5000 in) → RDS (5432 in), strict isolation  
**Application**: Input validation, parameterized queries, XSS prevention, rate limiting, audit logging, AWS Secrets Manager for credentials

---

## 7. Infrastructure Design

### 7.1 AWS Resources

**Compute**: ECS Fargate cluster, 0.5 vCPU/1GB tasks, 2-10 instances with auto-scaling at 70% CPU  
**Database**: RDS PostgreSQL 15 (db.t3.medium), Multi-AZ, 100GB, 7-day backups  
**Storage**: S3 buckets for prescriptions (private) and static assets (public + CloudFront)  
**Networking**: VPC 10.0.0.0/16, public/private subnets in 2 AZs, ALB with HTTPS/ACM certificate

**Monitoring**: CloudWatch metrics (requests, latency, errors, CPU/memory), alarms (CPU > 80%, errors > 5%), X-Ray tracing, log retention (30 days app, 7 years audit)

---

## 8. Integration Design

### 8.1 AWS Service Integration

**Transcribe Medical**: Synchronous API, temp S3 upload, poll for completion  
**Comprehend Medical**: Entity extraction (medications, symptoms, diagnoses)  
**Translate**: Batch translation with custom terminology  
**Cognito**: JWT validation using JWKS, automatic refresh

**Error Handling**: 3 retry attempts, fallback mechanisms, graceful degradation

---

## 9. Deployment Strategy

### 9.1 Environments

- **Development**: 1 ECS task, small RDS, synthetic data
- **Staging**: 2 ECS tasks, medium RDS, anonymized production data
- **Production**: 2-10 ECS tasks, Multi-AZ RDS, real data

### 9.2 CI/CD Pipeline

GitHub Actions workflow: Code quality → Testing (>70% coverage) → Build Docker image → Deploy to Staging → Manual approval → Production deployment with blue-green strategy and automatic rollback

**Database Migrations**: Alembic tool, Dev → Staging → Production flow, rollback via downgrade or snapshot restore

---

## 10. Performance & Testing

**Performance Optimization**: Database indexes and connection pooling, Gunicorn workers, code splitting, CloudFront CDN, Multi-AZ deployment. Targets: First Contentful Paint < 1.5s, Lighthouse Score > 90.

**Testing Strategy**: Unit tests (70%), Integration tests (20%), E2E tests (10%). Coverage: Overall > 70%, Critical paths > 90%.

---

---

## 11. AWS Integration & Deployment

### 11.1 AWS Services Configuration

**Cognito Setup**:
- User Pool with email verification
- App Client with USER_PASSWORD_AUTH flow
- JWT token validation (1-hour access, 30-day refresh)

**S3 Buckets**:
- Audio bucket: Server-side encryption (AES-256), lifecycle policies
- PDF bucket: Private access, presigned URLs (1-hour expiry)

**RDS Configuration**:
- PostgreSQL 15, Multi-AZ deployment
- Automated backups (7-day retention)
- Connection pooling (2-10 connections)
- Secrets Manager for credentials

**IAM Permissions**:
- ECS Task Role: Cognito, Transcribe, Comprehend, S3, Secrets Manager access
- Execution Role: ECR, CloudWatch Logs access

### 11.2 Deployment Process

**Pre-Deployment Validation**:
- DNS resolution for AWS endpoints
- HTTP connectivity tests
- AWS credentials validation
- Boto3 client creation tests

**Deployment Steps**:
1. Terraform infrastructure deployment
2. Docker image build and ECR push
3. ECS service update with new task definition
4. 90-second stabilization wait
5. Post-deployment health validation

**Post-Deployment Validation**:
- Basic health check (`/health`)
- AWS connectivity check (`/health/aws-connectivity`)
- Validates: Cognito, S3, Transcribe, Comprehend, Secrets Manager

**Rollback Procedure**:
- Revert to previous ECS task definition
- Database rollback via Alembic downgrade or snapshot restore
- Terraform state rollback if infrastructure changed

### 11.3 Monitoring & Operations

**Health Endpoints**:
- `/health` - Database, migrations, secrets manager status
- `/health/aws-connectivity` - All AWS services connectivity with latency metrics

**CloudWatch Metrics**:
- Request count, latency (p50, p95, p99)
- Error rates by endpoint
- ECS CPU/memory utilization
- Database connections and query performance

**Alarms**:
- CPU > 80% for 5 minutes
- Error rate > 5% for 2 minutes
- Health check failures
- Database connection pool exhaustion

**Log Retention**:
- Application logs: 30 days
- Audit logs: 7 years
- Access logs: 90 days

### 11.4 Troubleshooting

**Common Issues**:

1. **Connection Timeout**: Check NAT gateway status, security groups, VPC routes
2. **Authentication Failures**: Verify Cognito configuration, JWT token expiry
3. **Transcription Errors**: Check S3 permissions, audio format, file size limits
4. **Database Connection**: Verify RDS security group, Secrets Manager credentials

**Diagnostic Tools**:
- `test_aws_connectivity.py` - Comprehensive connectivity test
- `scripts/pre_deploy_check.sh` - Pre-deployment validation
- `scripts/validate_deployment.sh` - Post-deployment validation
- CloudWatch Logs Insights for query analysis

---

## Document Navigation

For requirements, user stories, acceptance criteria, and visual diagrams, refer to **requirements.md**.  
For deployment procedures and AWS configuration, refer to **README.md**.

**Version**: 2.0 | **Status**: Approved | **Last Updated**: 2026-03-01 | **Next Review**: 2026-04-01
