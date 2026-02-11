# SEVA Arogya - Requirements & Planning Document

**Version**: 2.0  
**Last Updated**: 2026-02-11  
**Status**: Approved for Development

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview](#2-system-overview)
3. [Core Features](#3-core-features)
4. [Nice-to-Have Features](#4-nice-to-have-features)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Technical Requirements](#6-technical-requirements)
7. [User Stories](#7-user-stories)
8. [Acceptance Criteria](#8-acceptance-criteria)
9. [Constraints & Assumptions](#9-constraints--assumptions)
10. [Success Metrics](#10-success-metrics)
11. [Risks & Mitigation](#11-risks--mitigation)
12. [Future Enhancements](#12-future-enhancements)
13. [Visual Diagrams](#13-visual-diagrams)
14. [Glossary](#14-glossary)

---

## 1. Executive Summary

SEVA Arogya is a voice-enabled clinical note capture and prescription generation system designed specifically for Indian healthcare settings. The system enables doctors to dictate clinical notes, automatically structures them into prescriptions, and generates professional, multi-language prescription documents.

### 1.1 Purpose
To provide doctors with an AI-powered voice assistant that:
- Reduces prescription writing time by 70%
- Eliminates handwriting legibility issues
- Supports multiple Indian languages
- Maintains medical accuracy and compliance
- Integrates seamlessly into existing clinical workflows

### 1.2 Target Users
- **Primary**: Doctors in OPD settings (clinics, hospitals)
- **Secondary**: Patients receiving prescriptions
- **Future**: Clinic administrators, healthcare systems

### 1.3 Key Differentiators
- Medical-domain optimized speech recognition
- Indian accent and terminology support
- Context-aware medication suggestions
- Multi-language prescription output
- Cloud-based, scalable architecture

---

## 2. System Overview

### 2.1 High-Level Architecture

```
┌─────────────┐
│   Doctor    │
│  (Browser)  │
└──────┬──────┘
       │ Voice Input
       ▼
┌─────────────────────────────────────────┐
│         React Frontend                  │
│  - Voice Recording                      │
│  - Prescription Form                    │
│  - Real-time Updates                    │
└──────┬──────────────────────────────────┘
       │ HTTPS + JWT
       ▼
┌─────────────────────────────────────────┐
│    Flask Backend (AWS ECS Fargate)      │
│  - Authentication                       │
│  - Voice Processing                     │
│  - NLP & Structuring                    │
│  - Suggestion Engine                    │
│  - PDF Generation                       │
└──────┬──────────────────────────────────┘
       │
       ├──────────────┬──────────────┐
       ▼              ▼              ▼
┌──────────┐   ┌──────────┐   ┌──────────┐
│ AWS AI   │   │   RDS    │   │   S3     │
│ Services │   │PostgreSQL│   │  PDFs    │
└──────────┘   └──────────┘   └──────────┘
```

### 2.2 Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 18+ | User interface |
| Backend | Flask (Python) | API and business logic |
| Database | PostgreSQL (RDS) | Data persistence |
| Storage | AWS S3 | PDF storage |
| Auth | AWS Cognito | User authentication |
| STT | AWS Transcribe Medical | Speech-to-text |
| NLP | AWS Comprehend Medical | Entity extraction |
| Translation | AWS Translate | Multi-language support |
| Hosting | AWS ECS Fargate | Container hosting |
| Load Balancer | AWS ALB | Traffic distribution |


---

## 3. Core Features

### 3.1 Voice-to-Text Clinical Note Capture (HIGH PRIORITY)

**Description**: Allow doctors to narrate clinical notes via voice with real-time transcription.

**Requirements**:
- Capture audio from device microphone
- Transcribe speech to text in near real-time (< 2 seconds)
- Support medical terminology and drug names
- Handle Indian English accents
- Support Hindi language input (future enhancement)
- Mark low-confidence words for review
- Provide visual feedback during recording

**Acceptance Criteria**:
- ✓ 90% overall transcription accuracy
- ✓ 98% accuracy for common medical terms (100+ term test set)
- ✓ 2-second maximum latency from speech end to text display
- ✓ Handle 20 short dictations per minute per user
- ✓ Graceful handling of background noise

### 3.2 Automatic Note Structuring (HIGH PRIORITY)

**Description**: Convert transcribed free-text into structured prescription elements.

**Requirements**:
- Extract and categorize:
  - Patient information (name, age, gender)
  - Clinical complaints/symptoms with duration
  - Vital signs (BP, temperature, heart rate, etc.)
  - Diagnoses or assessments
  - Medications (name, dosage, frequency, duration)
  - Additional instructions and advice
- Populate digital prescription template automatically
- Place unrecognized information in "Notes" section
- Support real-time updates as new voice input arrives

**Acceptance Criteria**:
- ✓ 90% field population accuracy (9/10 test prescriptions)
- ✓ All dictated information preserved (no data loss)
- ✓ Correct categorization of medications vs instructions
- ✓ Support for complex medical sentences
- ✓ Manual override capability without data loss

### 3.3 Smart Suggestion Engine (HIGH PRIORITY)

**Description**: Provide context-aware suggestions for medications and care instructions.

**Requirements**:
- Analyze current context (diagnosis, symptoms, patient info)
- Query doctor's prescription history
- Reference standard treatment guidelines
- Suggest:
  - Medications based on diagnosis
  - Common dosages and frequencies
  - Standard instructions (e.g., "Take after food")
  - Follow-up advice
- Learn from doctor's preferences over time
- Present suggestions non-intrusively
- Allow one-click acceptance or easy dismissal
- Never auto-add without user confirmation

**Acceptance Criteria**:
- ✓ 80% suggestion relevance (8/10 test scenarios)
- ✓ Non-intrusive UI (user feedback validation)
- ✓ Adaptive learning (Drug A becomes top suggestion after 5 uses)
- ✓ Optional toggle to disable suggestions
- ✓ Response time < 500ms for suggestion generation

### 3.4 Multi-Language Output (MEDIUM PRIORITY)

**Description**: Generate prescriptions in multiple languages (English and Hindi initially).

**Requirements**:
- Support English and Hindi output
- Allow per-prescription language selection
- Maintain default language preference in doctor profile
- Translate:
  - Symptom descriptions
  - Diagnosis text
  - Instructions and advice
- Preserve medical terms (drug names, units) without translation
- Use custom terminology glossary for accuracy
- Display preview before finalization

**Acceptance Criteria**:
- ✓ Accurate Hindi translation (4/5 prescriptions validated by bilingual expert)
- ✓ Medical terms remain unchanged
- ✓ Proper Hindi script rendering in PDF
- ✓ Grammar and spelling correctness
- ✓ Fallback to English on translation failure

### 3.5 Secure Doctor Login & Profile (HIGH PRIORITY)

**Description**: Implement secure authentication with personalized doctor profiles.

**Requirements**:
- User registration with:
  - Name, email/phone
  - Professional ID/registration number
  - Clinic/hospital name
  - Qualifications
- Secure login (JWT-based authentication)
- Password requirements enforcement
- Optional OTP-based login
- Profile management:
  - Preferred prescription language
  - Clinic letterhead information
  - Frequently used medications list
  - Digital signature (optional)
- Data isolation (doctors access only their own data)

**Acceptance Criteria**:
- ✓ Successful registration and login flow
- ✓ Password hashing (bcrypt or similar)
- ✓ JWT token validation on all API calls
- ✓ 401 error for invalid/expired tokens
- ✓ Profile updates persist correctly
- ✓ No cross-doctor data access

### 3.6 Standardized Digital Prescription (HIGH PRIORITY)

**Description**: Generate professional, legible prescription documents.

**Requirements**:
- PDF format output
- Standard layout including:
  - Header (doctor info, clinic, date)
  - Patient information
  - Symptoms/Complaints section
  - Diagnosis section
  - Medications table (name, dosage, frequency, duration)
  - Instructions/Advice section
  - Footer (disclaimers, follow-up info)
- A4 paper format
- Multi-page support with repeated headers
- Download and print options
- Optional email/WhatsApp sharing
- Store copy in database for audit

**Acceptance Criteria**:
- ✓ All structured fields appear in PDF
- ✓ Consistent formatting across prescriptions
- ✓ Font size ≥ 11pt for body text
- ✓ Clear medication table layout
- ✓ PDF generation < 3 seconds
- ✓ File size < 200KB per prescription
- ✓ Print-ready output (no cut-off sections)


---

## 4. Nice-to-Have Features (Future Scope)

### 4.1 Voice Commands & Macros (LOW PRIORITY)
- Voice commands: "next line", "new prescription", "undo"
- Reusable templates for common instructions
- Custom macros per doctor

### 4.2 Patient Record Integration
- Store basic patient data (name, age, history)
- Retrieve past prescriptions for follow-ups
- Patient search functionality

### 4.3 Ambient Conversation Capture
- Continuous listening mode (with consent)
- Auto-generate SOAP notes from conversation
- Advanced NLP for context understanding

### 4.4 EHR/Clinic System Integration
- APIs for EMR system integration
- Data export to hospital systems
- Billing system integration

### 4.5 Regulatory Compliance Features
- DISHA (India) compliance
- Patient consent management
- Advanced audit trails
- Data anonymization for research

---

## 5. Non-Functional Requirements

### 5.1 Performance

**Latency**:
- Transcription: < 2 seconds for 5-10 second audio
- UI interactions: < 300ms response time
- End-to-end prescription: 2-3 minutes total
- API response time: < 500ms (excluding external services)

**Throughput**:
- Support 50 concurrent users initially
- Scale to 500+ concurrent users
- Handle 20 dictations/minute per user

**Scalability**:
- Horizontal scaling of backend services
- Auto-scaling based on load (CPU/memory)
- Linear performance degradation with user growth

### 5.2 Reliability & Availability

**Uptime**:
- 99.5% availability target
- Especially during clinic hours (9 AM - 6 PM)
- Zero-downtime deployments
- Scheduled maintenance during off-hours

**Fault Tolerance**:
- Graceful error handling
- User-friendly error messages
- Partial data preservation on failure
- Retry mechanisms for transient failures
- Multi-AZ database deployment

**Data Durability**:
- No data loss for saved prescriptions
- Automated database backups
- Point-in-time recovery capability
- 99.999999999% S3 durability

### 5.3 Security

**Authentication & Authorization**:
- HTTPS for all communications
- JWT-based authentication
- Token expiration (1 hour)
- Refresh token mechanism
- Role-based access control
- Data isolation per doctor

**Data Protection**:
- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.2+)
- Secure password storage (hashed)
- No plaintext credentials
- Secrets management (AWS Secrets Manager)

**Audit & Compliance**:
- Audit logs for all actions
- Login/logout tracking
- Prescription creation logging
- IP address logging
- Compliance with Indian IT security practices
- DISHA-ready architecture

**Application Security**:
- XSS protection
- CSRF protection (JWT-based)
- SQL injection prevention
- Input validation
- Rate limiting
- Content Security Policy headers

### 5.4 Usability

**User Interface**:
- Intuitive, minimal-click design
- One-tap record/stop functionality
- Clear visualization of structured fields
- Easy text editing capability
- Responsive design (desktop, tablet, mobile)
- Legible fonts and adequate text sizes
- Real-time feedback (spinners, progress bars)

**Target Devices**:
- Primary: Desktop/Laptop (Chrome, Firefox)
- Secondary: Tablets
- Future: Mobile phones

**Accessibility**:
- Keyboard navigation support
- Screen reader compatibility (future)
- High contrast mode (future)

### 5.5 Maintainability & Extensibility

**Code Organization**:
- Modular architecture (frontend, backend, services)
- Clear separation of concerns
- Documented APIs and data models
- Consistent coding standards
- Version control (Git)

**Configuration Management**:
- Environment-based configuration
- Feature flags for gradual rollouts
- Database-driven vocabulary updates
- No code changes for common updates

**Testing**:
- Unit tests for critical components
- Integration tests for API endpoints
- End-to-end tests for user flows
- Automated test execution in CI/CD
- Code coverage > 70%

**Documentation**:
- API documentation (OpenAPI/Swagger)
- Database schema documentation
- Deployment guides
- Developer onboarding documentation
- Architecture decision records

**Extensibility**:
- Plugin architecture for new languages
- Adapter pattern for external services
- Easy integration of new AI models
- Support for multiple STT/NLP providers

### 5.6 Cost Efficiency

**Infrastructure Costs**:
- Pay-per-use AWS services
- Auto-scaling to minimize idle resources
- Reserved instances for predictable load
- Cost monitoring and alerts
- Budget limits per user/clinic

**Development Efficiency**:
- Use managed services (reduce ops overhead)
- Focus on core differentiators
- Leverage existing platforms (Cognito, RDS)
- Avoid reinventing commodity features

**Operational Costs**:
- Automated deployments (reduce manual effort)
- Self-healing infrastructure
- Minimal manual intervention
- Efficient resource utilization


---

## 6. Technical Requirements

### 6.1 Frontend Requirements

**Technology Stack**:
- React 18+
- JavaScript/TypeScript
- State Management: Redux or Context API
- HTTP Client: Axios or Fetch API
- UI Framework: Material-UI or Tailwind CSS

**Functionality**:
- Web Audio API for microphone access
- Real-time state updates
- Form validation
- PDF preview and download
- Responsive layout
- Progressive Web App (PWA) capability (future)

### 6.2 Backend Requirements

**Technology Stack**:
- Python 3.9+
- Flask web framework
- Gunicorn WSGI server
- SQLAlchemy ORM
- Boto3 (AWS SDK)
- Docker containerization

**API Endpoints**:
- POST /auth/register - User registration
- POST /auth/login - User login
- POST /auth/refresh - Token refresh
- GET /profile - Get doctor profile
- PUT /profile - Update doctor profile
- POST /transcribe - Audio transcription
- POST /analyze - Text analysis and structuring
- GET /suggest - Get medication suggestions
- POST /prescriptions - Create prescription
- GET /prescriptions - List prescriptions
- GET /prescriptions/{id} - Get specific prescription

**Services**:
- Authentication service
- Transcription service
- NLP/structuring service
- Suggestion engine
- PDF generation service
- Database access layer

### 6.3 Database Requirements

**Technology**: PostgreSQL 13+ on AWS RDS

**Tables**:
- doctors (user profiles)
- prescriptions (prescription records)
- prescription_medications (medication details)
- medications_master (reference data)
- audit_logs (security audit trail)

**Features**:
- ACID compliance
- Foreign key constraints
- Indexes on frequently queried fields
- JSON support for semi-structured data
- Full-text search capability (future)

### 6.4 External Services

**AWS Transcribe Medical**:
- Medical vocabulary support
- Indian English accent support
- Real-time or batch transcription
- Custom vocabulary (optional)

**AWS Comprehend Medical**:
- Entity extraction (medications, symptoms, dosages)
- Relationship detection
- Medical ontology mapping

**AWS Translate**:
- English to Hindi translation
- Custom terminology support
- Batch translation capability

**AWS Cognito**:
- User pool management
- JWT token generation
- Password policies
- MFA support (optional)

**AWS S3**:
- PDF storage
- Static asset hosting
- Versioning enabled
- Lifecycle policies

**AWS CloudWatch**:
- Application logs
- Metrics and monitoring
- Alarms and notifications

### 6.5 Infrastructure Requirements

**Deployment Platform**: AWS ECS Fargate

**Networking**:
- VPC with public and private subnets
- Multi-AZ deployment
- Application Load Balancer (HTTPS)
- NAT Gateway for outbound traffic
- Security Groups for access control

**Compute**:
- ECS Fargate tasks (2-10 instances)
- Auto-scaling based on CPU/memory
- Health checks and automatic recovery

**Storage**:
- RDS PostgreSQL (Multi-AZ)
- S3 buckets (prescriptions, static assets)
- EBS volumes for container storage

**Security**:
- AWS WAF (optional)
- AWS Secrets Manager
- IAM roles and policies
- SSL/TLS certificates (ACM)

**CI/CD**:
- GitHub Actions or AWS CodePipeline
- Automated testing
- Docker image building
- ECR for container registry
- Automated deployment to ECS


---

## 7. User Stories

### 7.1 Doctor Stories

**Story 1: Quick Voice Prescription**
- **As a** busy doctor in an OPD
- **I want to** quickly record patient findings by speaking
- **So that** I spend less time writing and maintain eye contact with patients
- **Acceptance**: Text appears correctly within 2 seconds, natural workflow

**Story 2: Automatic Structuring**
- **As a** doctor
- **I want** the system to automatically organize my notes into prescription format
- **So that** I don't manually structure or rewrite anything
- **Acceptance**: Prescription fields auto-filled, professional appearance

**Story 3: Smart Suggestions**
- **As a** doctor
- **I want** medication suggestions based on diagnosis
- **So that** I save time and follow standard care practices
- **Acceptance**: Relevant suggestions, one-click acceptance, faster completion

**Story 4: Error Correction**
- **As a** doctor concerned about errors
- **I want to** easily review and edit the output
- **So that** I maintain 100% control over prescription accuracy
- **Acceptance**: Easy editing, immediate updates, no data loss

**Story 5: Multi-Language Support**
- **As a** multilingual doctor
- **I want to** give prescriptions in patient's local language
- **So that** patients can read and understand better
- **Acceptance**: Accurate Hindi translation, easy language toggle

**Story 6: Professional Output**
- **As a** doctor
- **I want** uniform, clear prescriptions with my letterhead
- **So that** they look professional and can be referenced later
- **Acceptance**: Consistent format, includes letterhead, fits on one page

### 7.2 Patient Stories

**Story 7: Legible Prescription**
- **As a** patient
- **I want** typed, clearly printed prescriptions
- **So that** I can follow instructions correctly without misreading
- **Acceptance**: Easy to read, clear formatting, unambiguous details

**Story 8: Language Preference**
- **As a** patient who prefers Hindi
- **I want** prescriptions in my language
- **So that** I can understand instructions without help
- **Acceptance**: Accurate translation, readable script, clear instructions

### 7.3 Administrator Stories

**Story 9: Data Security**
- **As a** clinic admin
- **I want** secure storage and backups of doctor/patient data
- **So that** we comply with regulations and can recover information
- **Acceptance**: Secure login, encrypted storage, audit logs, data recovery

**Story 10: System Maintenance**
- **As a** product owner
- **I want** easy system updates and feature additions
- **So that** the product stays current with medical advancements
- **Acceptance**: Modular architecture, clear documentation, automated deployment

---

## 8. Acceptance Criteria Summary

### 8.1 Voice Transcription
- ✓ 90% overall accuracy
- ✓ 98% accuracy for 100+ common medical terms
- ✓ < 2 second latency
- ✓ 20 dictations/minute capacity
- ✓ Graceful noise handling
- ✓ Low-confidence word flagging

### 8.2 Data Structuring
- ✓ 90% field population accuracy
- ✓ Zero data loss
- ✓ Correct categorization
- ✓ Manual override support
- ✓ Real-time updates

### 8.3 Suggestions
- ✓ 80% relevance rate
- ✓ Non-intrusive UI
- ✓ Adaptive learning (5 iterations)
- ✓ Optional disable
- ✓ < 500ms response time

### 8.4 Multi-Language
- ✓ 80% translation accuracy (4/5 validated)
- ✓ Medical terms preserved
- ✓ Proper script rendering
- ✓ Grammar correctness
- ✓ Fallback mechanism

### 8.5 Authentication
- ✓ Successful registration/login
- ✓ Secure password storage
- ✓ JWT validation
- ✓ Token expiration handling
- ✓ Data isolation

### 8.6 PDF Generation
- ✓ All fields present
- ✓ Consistent formatting
- ✓ Font size ≥ 11pt
- ✓ < 3 second generation
- ✓ < 200KB file size
- ✓ Print-ready output

### 8.7 Performance
- ✓ 50 concurrent users
- ✓ 99.5% uptime
- ✓ < 300ms UI response
- ✓ Auto-scaling functional
- ✓ Zero data loss

### 8.8 Security
- ✓ HTTPS everywhere
- ✓ Encryption at rest
- ✓ Audit logging
- ✓ No cross-user access
- ✓ Secure secrets management

---

## 9. Constraints & Assumptions

### 9.1 Constraints

**Technical**:
- Must use AWS cloud services
- Must support Chrome and Firefox browsers
- Initial deployment in AWS ap-south-1 (Mumbai) region
- Must work with standard clinic internet connections (2+ Mbps)

**Business**:
- MVP budget constraints (use managed services)
- 6-month initial development timeline
- Focus on OPD use case first
- English and Hindi languages only (initially)

**Regulatory**:
- Must align with Indian IT security practices
- Must prepare for DISHA compliance
- Must maintain audit trails
- Must ensure data residency in India

**Operational**:
- Minimal manual intervention required
- Must support remote deployment
- Must allow zero-downtime updates
- Must provide self-service doctor onboarding

### 9.2 Assumptions

**User Assumptions**:
- Doctors have basic computer literacy
- Doctors speak English or Hindi for dictation
- Doctors have access to microphone-enabled devices
- Patients accept digital prescriptions

**Technical Assumptions**:
- AWS services available in Mumbai region
- Transcribe Medical supports Indian English
- Comprehend Medical accuracy sufficient for use case
- Internet connectivity available during consultations

**Business Assumptions**:
- Doctors willing to adopt voice-based system
- Cost per transcription acceptable for clinic economics
- Market demand for digital prescription solutions
- Regulatory environment favorable for health tech


---

## 10. Success Metrics

### 10.1 User Adoption
- 100+ active doctors within 6 months
- 1000+ prescriptions generated per month
- 70% daily active user rate
- < 5% user churn rate

### 10.2 Performance Metrics
- 95% transcription accuracy (user-reported)
- < 2 minute average prescription time
- 99.5% system uptime
- < 1% error rate

### 10.3 Business Metrics
- 70% reduction in prescription writing time
- 90% user satisfaction score
- 50% reduction in prescription errors
- Positive ROI within 12 months

### 10.4 Quality Metrics
- Zero security breaches
- Zero data loss incidents
- < 10 critical bugs per release
- 90% test coverage

---

## 11. Risks & Mitigation

### 11.1 Technical Risks

**Risk**: Transcription accuracy insufficient
- **Mitigation**: Custom vocabulary, user feedback loop, manual correction

**Risk**: AWS service outages
- **Mitigation**: Multi-AZ deployment, graceful degradation, offline mode (future)

**Risk**: Performance degradation under load
- **Mitigation**: Auto-scaling, load testing, performance monitoring

### 11.2 Business Risks

**Risk**: Low user adoption
- **Mitigation**: User training, onboarding support, iterative improvements

**Risk**: Cost overruns
- **Mitigation**: Cost monitoring, usage limits, optimization reviews

**Risk**: Regulatory changes
- **Mitigation**: Modular architecture, compliance monitoring, legal consultation

### 11.3 Security Risks

**Risk**: Data breach
- **Mitigation**: Encryption, access controls, security audits, penetration testing

**Risk**: Unauthorized access
- **Mitigation**: Strong authentication, JWT expiration, audit logging

---

## 12. Future Enhancements

### Phase 2 (6-12 months)
- Patient record management
- Prescription history and search
- Mobile app (iOS/Android)
- Additional regional languages (Tamil, Telugu, Bengali)
- Voice commands and macros

### Phase 3 (12-18 months)
- Ambient conversation capture
- EHR system integration
- Advanced analytics and insights
- Telemedicine integration
- Multi-clinic management

### Phase 4 (18-24 months)
- AI-powered diagnosis assistance
- Drug interaction warnings
- Clinical decision support
- Research data aggregation
- International expansion

# SEVA Arogya - System Diagrams

## 1. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SEVA Arogya System                            │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│   Doctor's Browser   │
│   (React Web App)    │
│                      │
│  - Voice Recording   │
│  - Prescription Form │
│  - PDF Preview       │
└──────────┬───────────┘
           │ HTTPS
           │ (JWT Token)
           ▼
┌──────────────────────┐
│  Application Load    │
│     Balancer         │
│   (Port 443/HTTPS)   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│              AWS ECS Fargate (Flask Backend)                 │
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │  Auth      │  │Transcription│  │ Suggestion │             │
│  │  Module    │  │   Module    │  │   Engine   │             │
│  └────────────┘  └────────────┘  └────────────┘              │
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │    NLP     │  │    PDF     │  │  Database  │              │
│  │  Module    │  │ Generator  │  │   Access   │              │
│  └────────────┘  └────────────┘  └────────────┘              │
└──────────┬───────────────────────────────────┬────────────  ─┘
           │                                   │
           │                                   ▼
           │                          ┌─────────────────┐
           │                          │   AWS RDS       │
           │                          │  (PostgreSQL)   │
           │                          │                 │
           │                          │ - Doctors       │
           │                          │ - Prescriptions │
           │                          │ - Medications   │
           │                          └─────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│                    AWS AI Services                           │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                  │
│  │  AWS Transcribe  │  │ AWS Comprehend   │                  │
│  │    Medical       │  │    Medical       │                  │
│  │                  │  │                  │                  │
│  │ - Speech to Text │  │ - Entity Extract │                  │
│  │ - Medical Terms  │  │ - Medications    │                  │
│  │ - Indian Accent  │  │ - Symptoms       │                  │
│  └──────────────────┘  └──────────────────┘                  │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                  │
│  │  AWS Translate   │  │   AWS Cognito    │                  │
│  │                  │  │                  │                  │
│  │ - Multi-language │  │ - User Auth      │                  │
│  │ - Hindi Support  │  │ - JWT Tokens     │                  │
│  └──────────────────┘  └──────────────────┘                  │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────┐
│      AWS S3          │
│                      │
│ - Prescription PDFs  │
│ - Static Assets      │
└──────────────────────┘
```


## 2. Data Flow Diagram (DFD) - Level 0

```
                    ┌─────────────┐
                    │   Doctor    │
                    └──────┬──────┘
                           │
                           │ Voice Input + Patient Info
                           ▼
        ┌──────────────────────────────────────┐
        │                                      │
        │      SEVA Arogya System              │
        │   (Voice-to-Prescription Platform)   │
        │                                      │
        └──────────────────┬───────────────────┘
                           │
                           │ Digital Prescription (PDF)
                           ▼
                    ┌─────────────┐
                    │   Patient   │
                    └─────────────┘
```

## 3. Data Flow Diagram (DFD) - Level 1

```
┌─────────┐
│ Doctor  │
└────┬────┘
     │
     │ 1. Audio Recording
     ▼
┌─────────────────────┐
│  1.0 Capture Voice  │
│     & Transcribe    │
└─────────┬───────────┘
          │
          │ 2. Transcribed Text
          ▼
┌─────────────────────┐         ┌──────────────┐
│  2.0 Structure &    │────────▶│  D1: Doctor │
│  Extract Entities   │         │   Profiles   │
└─────────┬───────────┘         └──────────────┘
          │
          │ 3. Structured Data
          ▼
┌─────────────────────┐         ┌──────────────┐
│  3.0 Generate       │────────▶│ D2: Medicine │
│    Suggestions      │◀────────│   Database   │
└─────────┬───────────┘         └──────────────┘
          │
          │ 4. Suggestions + Structured Data
          ▼
┌─────────────────────┐
│  4.0 Review &       │
│     Finalize        │
└─────────┬───────────┘
          │
          │ 5. Final Prescription Data
          ▼
┌─────────────────────┐         ┌──────────────┐
│  5.0 Generate PDF   │────────▶│D3: Prescription
│  & Store            │         │   Records    │
└─────────┬───────────┘         └──────────────┘
          │
          │ 6. PDF Document
          ▼
     ┌─────────┐
     │ Patient │
     └─────────┘
```


## 4. Sequence Diagram - Complete Prescription Flow

```
Doctor    React App    ALB    Flask API    Cognito    Transcribe    Comprehend    RDS    S3
  │           │         │         │           │            │             │         │     │
  │──Login───▶│         │         │           │            │             │         │     │
  │           │─────────┼────────▶│           │            │             │         │     │
  │           │         │         │──Verify──▶│            │             │         │     │
  │           │         │         │◀──JWT─────│            │             │         │     │
  │           │◀────────┼─────────│           │            │             │         │     │
  │           │         │         │           │            │             │         │     │
  │──Record──▶│         │         │           │            │             │         │     │
  │  Voice    │         │         │           │            │             │         │     │
  │           │         │         │           │            │             │         │     │
  │           │─Audio───┼────────▶│           │            │             │         │     │
  │           │ +JWT    │         │           │            │             │         │     │
  │           │         │         │──Audio───▶│            │             │         │     │
  │           │         │         │           │──Process──▶│             │         │     │
  │           │         │         │           │◀───Text────│             │         │     │
  │           │         │         │◀──Text────│            │             │         │     │
  │           │         │         │                        │             │         │     │
  │           │         │         │────Text───────────────▶│             │         │     │
  │           │         │         │◀──Entities─────────────│             │         │     │
  │           │         │         │                        │             │         │     │
  │           │         │         │──Query Suggestions────────────────────────────▶│     │
  │           │         │         │◀──Past Data───────────────────────────────────│     │
  │           │         │         │                        │             │         │     │
  │           │◀────────┼─────────│           │            │             │         │     │
  │           │ Structured Data   │           │            │             │         │     │
  │◀─Display──│         │         │           │            │             │         │     │
  │           │         │         │           │            │             │         │     │
  │──Edit &──▶│         │         │           │            │             │         │     │
  │  Review   │         │         │           │            │             │         │     │
  │           │         │         │           │            │             │         │     │
  │──Finalize─▶│         │         │           │            │             │         │     │
  │           │         │         │           │            │             │         │     │
  │           │─Final───┼────────▶│           │            │             │         │     │
  │           │  Data   │         │           │            │             │         │     │
  │           │         │         │──Save────────────────────────────────────────▶│     │
  │           │         │         │◀──Saved──────────────────────────────────────│     │
  │           │         │         │                        │             │         │     │
  │           │         │         │──Generate PDF─────────────────────────────────────▶│
  │           │         │         │◀──PDF URL─────────────────────────────────────────│
  │           │         │         │                        │             │         │     │
  │           │◀────────┼─────────│           │            │             │         │     │
  │◀──PDF─────│         │         │           │            │             │         │     │
  │  Download │         │         │           │            │             │         │     │
  │           │         │         │           │            │             │         │     │
```


## 5. Database Schema Diagram

```
┌─────────────────────────────────────────┐
│              Doctors                    │
├─────────────────────────────────────────┤
│ PK  doctor_id         INT               │
│     cognito_sub       VARCHAR(255)      │
│     name              VARCHAR(255)      │
│     email             VARCHAR(255)      │
│     phone             VARCHAR(20)       │
│     clinic_name       VARCHAR(255)      │
│     qualifications    TEXT              │
│     preferred_lang    VARCHAR(10)       │
│     created_at        TIMESTAMP         │
│     updated_at        TIMESTAMP         │
└─────────────────────────────────────────┘
                │
                │ 1:N
                ▼
┌─────────────────────────────────────────┐
│           Prescriptions                 │
├─────────────────────────────────────────┤
│ PK  prescription_id   INT               │
│ FK  doctor_id         INT               │
│     patient_name      VARCHAR(255)      │
│     patient_age       INT               │
│     patient_gender    VARCHAR(10)       │
│     symptoms          TEXT              │
│     vitals            TEXT              │
│     diagnosis         TEXT              │
│     instructions      TEXT              │
│     language          VARCHAR(10)       │
│     pdf_url           VARCHAR(500)      │
│     created_at        TIMESTAMP         │
└─────────────────────────────────────────┘
                │
                │ 1:N
                ▼
┌─────────────────────────────────────────┐
│        Prescription_Medications         │
├─────────────────────────────────────────┤
│ PK  med_id            INT               │
│ FK  prescription_id   INT               │
│     medication_name   VARCHAR(255)      │
│     dosage            VARCHAR(100)      │
│     frequency         VARCHAR(100)      │
│     duration          VARCHAR(100)      │
│     instructions      TEXT              │
│     created_at        TIMESTAMP         │
└─────────────────────────────────────────┘


┌─────────────────────────────────────────┐
│        Medications_Master               │
├─────────────────────────────────────────┤
│ PK  medication_id     INT               │
│     name              VARCHAR(255)      │
│     generic_name      VARCHAR(255)      │
│     category          VARCHAR(100)      │
│     common_dosages    TEXT              │
│     common_frequency  TEXT              │
│     typical_duration  VARCHAR(100)      │
│     created_at        TIMESTAMP         │
└─────────────────────────────────────────┘


┌─────────────────────────────────────────┐
│            Audit_Logs                   │
├─────────────────────────────────────────┤
│ PK  log_id            INT               │
│ FK  doctor_id         INT               │
│     action            VARCHAR(100)      │
│     details           TEXT              │
│     ip_address        VARCHAR(50)       │
│     timestamp         TIMESTAMP         │
└─────────────────────────────────────────┘
```


## 6. AWS Infrastructure Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                          AWS Cloud (ap-south-1)                        │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    Public Subnet (AZ-1)                      │    │
│  │                                                            │    │
│  │  ┌────────────────────────────────────────────┐            │    │
│  │  │   Application Load Balancer (ALB)          │            │    │
│  │  │   - HTTPS (Port 443)                       │            │    │
│  │  │   - SSL Certificate (ACM)                  │            │    │
│  │  │   - Health Checks                          │            │    │
│  │  └────────────────┬───────────────────────────┘            │    │
│  └───────────────────┼────────────────────────────────────────┘    │
│                      │                                              │
│  ┌───────────────────┼────────────────────────────────────────┐    │
│  │                   │   Private Subnet (AZ-1 & AZ-2)         │    │
│  │                   ▼                                        │    │
│  │  ┌─────────────────────────────────────────────────┐      │    │
│  │  │      ECS Fargate Cluster                        │      │    │
│  │  │                                                 │      │    │
│  │  │  ┌──────────────┐      ┌──────────────┐       │      │    │
│  │  │  │ Flask Task 1 │      │ Flask Task 2 │       │      │    │
│  │  │  │ (Container)  │      │ (Container)  │       │      │    │
│  │  │  └──────────────┘      └──────────────┘       │      │    │
│  │  │                                                 │      │    │
│  │  │  Auto-scaling: 2-10 tasks                      │      │    │
│  │  └─────────────────┬───────────────────────────────┘      │    │
│  │                    │                                      │    │
│  │                    ▼                                      │    │
│  │  ┌─────────────────────────────────────────────────┐      │    │
│  │  │      Amazon RDS (PostgreSQL)                    │      │    │
│  │  │      - Multi-AZ Deployment                      │      │    │
│  │  │      - Encrypted at Rest                        │      │    │
│  │  │      - Automated Backups                        │      │    │
│  │  └─────────────────────────────────────────────────┘      │    │
│  └───────────────────────────────────────────────────────────┘    │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    AWS Managed Services                      │    │
│  │                                                              │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │    │
│  │  │   Cognito    │  │  Transcribe  │  │  Comprehend  │     │    │
│  │  │  User Pool   │  │   Medical    │  │   Medical    │     │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │    │
│  │                                                              │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │    │
│  │  │  Translate   │  │      S3      │  │  CloudWatch  │     │    │
│  │  │              │  │   Buckets    │  │    Logs      │     │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │    │
│  │                                                              │    │
│  │  ┌──────────────┐  ┌──────────────┐                        │    │
│  │  │   Secrets    │  │     X-Ray    │                        │    │
│  │  │   Manager    │  │   Tracing    │                        │    │
│  │  └──────────────┘  └──────────────┘                        │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    CI/CD Pipeline                            │    │
│  │                                                              │    │
│  │  GitHub Actions / CodePipeline                              │    │
│  │  ├─ Build Docker Image                                      │    │
│  │  ├─ Push to ECR                                             │    │
│  │  ├─ Run Tests                                               │    │
│  │  └─ Deploy to ECS                                           │    │
│  └──────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────┘
```


## 7. Authentication Flow Diagram

```
┌─────────┐                                              ┌──────────────┐
│ Doctor  │                                              │   Cognito    │
│ Browser │                                              │  User Pool   │
└────┬────┘                                              └──────┬───────┘
     │                                                          │
     │ 1. Navigate to App                                      │
     ├──────────────────────────────────────────────────┐      │
     │                                                  │      │
     │ 2. Redirect to Login                             │      │
     ├─────────────────────────────────────────────────▶│      │
     │                                                  │      │
     │ 3. Enter Credentials                             │      │
     ├─────────────────────────────────────────────────▶│      │
     │                                                  │      │
     │                                                  │ 4. Validate
     │                                                  │      │
     │ 5. Return JWT Tokens                             │      │
     │    (ID Token, Access Token, Refresh Token)       │      │
     │◀─────────────────────────────────────────────────┤      │
     │                                                  │      │
     │ 6. Store Tokens (Memory/LocalStorage)            │      │
     │                                                         │
     │                                                         │
     │ 7. API Request with JWT                                │
     ├────────────────────────────────────────────────────────┼──────┐
     │                                                         │      │
     │                                              ┌──────────▼──────▼─┐
     │                                              │   Flask Backend   │
     │                                              │                   │
     │                                              │ 8. Verify JWT     │
     │                                              │    Signature      │
     │                                              │                   │
     │                                              │ 9. Check Expiry   │
     │                                              │                   │
     │ 10. Return Protected Resource                │ 11. Authorize     │
     │◀─────────────────────────────────────────────┤     Request       │
     │                                              └───────────────────┘
     │
     │
     │ [Token Expires After 1 Hour]
     │
     │ 12. API Request with Expired Token
     ├────────────────────────────────────────────────────────┐
     │                                              ┌──────────▼────────┐
     │                                              │  Flask Backend    │
     │                                              │                   │
     │ 13. Return 401 Unauthorized                  │ Token Expired     │
     │◀─────────────────────────────────────────────┤                   │
     │                                              └───────────────────┘
     │
     │ 14. Use Refresh Token                               │
     ├─────────────────────────────────────────────────────▶│
     │                                                       │
     │ 15. Return New Access Token                          │
     │◀──────────────────────────────────────────────────────┤
     │                                                       │
     │ 16. Retry API Request with New Token                 │
     ├───────────────────────────────────────────────────────┼──────┐
     │                                              ┌────────▼──────▼─┐
     │                                              │  Flask Backend   │
     │ 17. Success Response                         │                  │
     │◀─────────────────────────────────────────────┤  Process Request │
     │                                              └──────────────────┘
     │
```


## 8. Voice Processing Flowchart

```
                    START
                      │
                      ▼
            ┌─────────────────┐
            │ Doctor Presses  │
            │ Record Button   │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Capture Audio   │
            │ via Microphone  │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Doctor Stops    │
            │ Recording       │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Send Audio to   │
            │ Backend API     │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ AWS Transcribe  │
            │ Medical         │
            │ (Speech-to-Text)│
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
         ┌──│ Transcription   │
         │  │ Successful?     │
         │  └────────┬────────┘
         │           │
         │ No        │ Yes
         │           ▼
         │  ┌─────────────────┐
         │  │ AWS Comprehend  │
         │  │ Medical         │
         │  │ (Entity Extract)│
         │  └────────┬────────┘
         │           │
         │           ▼
         │           ▼
         │  ┌─────────────────┐
         │  │ Extract:        │
         │  │ - Symptoms      │
         │  │ - Medications   │
         │  │ - Dosages       │
         │  │ - Diagnosis     │
         │  └────────┬────────┘
         │           │
         │           ▼
         │  ┌─────────────────┐
         │  │ Query Suggestion│
         │  │ Engine          │
         │  └────────┬────────┘
         │           │
         │           ▼
         │  ┌─────────────────┐
         │  │ Generate        │
         │  │ Suggestions     │
         │  │ Based on:       │
         │  │ - Context       │
         │  │ - History       │
         │  │ - Guidelines    │
         │  └────────┬────────┘
         │           │
         │           ▼
         │  ┌─────────────────┐
         │  │ Return to       │
         │  │ Frontend:       │
         │  │ - Transcript    │
         │  │ - Entities      │
         │  │ - Suggestions   │
         │  └────────┬────────┘
         │           │
         │           ▼
         │  ┌─────────────────┐
         │  │ Update UI with  │
         │  │ Structured Data │
         │  └────────┬────────┘
         │           │
         │           ▼
         │  ┌─────────────────┐
         │  │ Doctor Reviews  │
         │  │ & Edits         │
         │  └────────┬────────┘
         │           │
         │           └──────────┐
         │                      │
         ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│ Show Error      │    │ Continue or     │
│ Message         │    │ Finalize        │
└────────┬────────┘    └────────┬────────┘
         │                      │
         │                      ▼
         │             ┌─────────────────┐
         │             │      END        │
         │             └─────────────────┘
         │
         └──────────────▶ Retry Option
```


## 9. Prescription Generation Flowchart

```
                    START
                      │
                      ▼
            ┌─────────────────┐
            │ Doctor Clicks   │
            │ "Finalize"      │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
         ┌──│ All Required    │
         │  │ Fields Present? │
         │  └────────┬────────┘
         │           │
         │ No        │ Yes
         │           ▼
         │  ┌─────────────────┐
         │  │ Compile         │
         │  │ Prescription    │
         │  │ Data            │
         │  └────────┬────────┘
         │           │
         │           ▼
         │  ┌─────────────────┐
         │  │ Check Output    │
         │  │ Language        │
         │  └────────┬────────┘
         │           │
         │           ├─────────────┐
         │           │             │
         │      English         Hindi/Other
         │           │             │
         │           │             ▼
         │           │    ┌─────────────────┐
         │           │    │ AWS Translate   │
         │           │    │ Instructions &  │
         │           │    │ Diagnosis       │
         │           │    └────────┬────────┘
         │           │             │
         │           └─────────────┘
         │                    │
         │                    ▼
         │           ┌─────────────────┐
         │           │ Save to RDS:    │
         │           │ - Prescription  │
         │           │ - Medications   │
         │           └────────┬────────┘
         │                    │
         │                    │
         │                    ▼
         │           ┌─────────────────┐
         │           │ Generate PDF    │
         │           │ Using Template: │
         │           │ - Header        │
         │           │ - Patient Info  │
         │           │ - Symptoms      │
         │           │ - Diagnosis     │
         │           │ - Medications   │
         │           │ - Instructions  │
         │           │ - Footer        │
         │           └────────┬────────┘
         │                    │
         │                    ▼
         │           ┌─────────────────┐
         │           │ Upload PDF to   │
         │           │ S3 Bucket       │
         │           └────────┬────────┘
         │                    │
         │                    ▼
         │           ┌─────────────────┐
         │           │ Update RDS with │
         │           │ PDF URL         │
         │           └────────┬────────┘
         │                    │
         │                    ▼
         │           ┌─────────────────┐
         │           │ Return PDF to   │
         │           │ Frontend        │
         │           └────────┬────────┘
         │                    │
         │                    ▼
         │           ┌─────────────────┐
         │           │ Display PDF     │
         │           │ Download/Print  │
         │           │ Options         │
         │           └────────┬────────┘
         │                    │
         │                    ▼
         │           ┌─────────────────┐
         │           │ Update          │
         │           │ Suggestion      │
         │           │ Engine History  │
         │           └────────┬────────┘
         │                    │
         │                    ▼
         │                   END
         │
         ▼
┌─────────────────┐
│ Show Validation │
│ Error Message   │
└────────┬────────┘
         │
         └──────────▶ Return to Form
```


## 10. Component Interaction Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                         React Frontend                             │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Login      │  │   Voice      │  │ Prescription │           │
│  │  Component   │  │  Recorder    │  │    Form      │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                 │                  │                    │
│         └─────────────────┼──────────────────┘                    │
│                           │                                       │
│                  ┌────────▼────────┐                              │
│                  │  State Manager  │                              │
│                  │ (Redux/Context) │                              │
│                  └────────┬────────┘                              │
│                           │                                       │
│                  ┌────────▼────────┐                              │
│                  │   API Service   │                              │
│                  │   (Axios/Fetch) │                              │
│                  └────────┬────────┘                              │
└───────────────────────────┼────────────────────────────────────────┘
                            │ HTTPS + JWT
                            │
┌───────────────────────────▼────────────────────────────────────────┐
│                      Flask Backend API                             │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                  Middleware Layer                        │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐        │    │
│  │  │    CORS    │  │    JWT     │  │   Error    │        │    │
│  │  │  Handler   │  │ Validator  │  │  Handler   │        │    │
│  │  └────────────┘  └────────────┘  └────────────┘        │    │
│  └──────────────────────────────────────────────────────────┘    │
│                           │                                       │
│  ┌────────────────────────┼──────────────────────────────┐       │
│  │              API Routes & Controllers                 │       │
│  │                        │                              │       │
│  │  ┌──────────┐  ┌──────▼─────┐  ┌──────────┐         │       │
│  │  │  /auth   │  │/transcribe │  │/prescriptions│      │       │
│  │  └──────────┘  └──────┬─────┘  └──────────┘         │       │
│  └─────────────────────────┼──────────────────────────────┘       │
│                            │                                      │
│  ┌─────────────────────────┼──────────────────────────────┐       │
│  │           Service Layer │                              │       │
│  │                         │                              │       │
│  │  ┌──────────┐  ┌────────▼────┐  ┌──────────────┐     │       │
│  │  │   Auth   │  │Transcription│  │     NLP      │     │       │
│  │  │ Service  │  │   Service   │  │   Service    │     │       │
│  │  └──────────┘  └────────┬────┘  └──────┬───────┘     │       │
│  │                         │               │             │       │
│  │  ┌──────────┐  ┌────────▼────┐  ┌──────▼───────┐     │       │
│  │  │Suggestion│  │     PDF     │  │   Database   │     │       │
│  │  │  Engine  │  │  Generator  │  │    Access    │     │       │
│  │  └──────────┘  └─────────────┘  └──────────────┘     │       │
│  └──────────────────────────────────────────────────────┘       │
│                            │                                      │
└────────────────────────────┼──────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐  ┌──────────────────┐  ┌──────────────┐
│  AWS Cognito  │  │   AWS Services   │  │   AWS RDS    │
│               │  │                  │  │ (PostgreSQL) │
│ - User Pool   │  │ - Transcribe     │  │              │
│ - JWT Tokens  │  │ - Comprehend     │  │ - Doctors    │
│               │  │ - Translate      │  │ - Rx Data    │
└───────────────┘  └──────────────────┘  └──────────────┘
                             │
                             ▼
                    ┌──────────────┐
                    │   AWS S3     │
                    │              │
                    │ - PDF Files  │
                    └──────────────┘
```


## 11. Network Security Architecture

```
                        Internet
                           │
                           │ HTTPS (443)
                           ▼
                  ┌─────────────────┐
                  │   AWS WAF       │
                  │ (Optional)      │
                  └────────┬────────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                          │           VPC                    │
│                          │                                  │
│  ┌───────────────────────▼──────────────────────────┐      │
│  │              Public Subnet                       │      │
│  │                                                  │      │
│  │  ┌────────────────────────────────────────┐     │      │
│  │  │  Application Load Balancer             │     │      │
│  │  │  Security Group: ALB-SG                │     │      │
│  │  │  Inbound: 443 from 0.0.0.0/0           │     │      │
│  │  │  Outbound: 5000 to ECS-SG              │     │      │
│  │  └────────────────┬───────────────────────┘     │      │
│  └───────────────────┼───────────────────────────────┘      │
│                      │                                      │
│  ┌───────────────────▼───────────────────────────────┐      │
│  │           Private Subnet (AZ-1)                   │      │
│  │                                                   │      │
│  │  ┌─────────────────────────────────────────┐     │      │
│  │  │  ECS Fargate Tasks                      │     │      │
│  │  │  Security Group: ECS-SG                 │     │      │
│  │  │  Inbound: 5000 from ALB-SG              │     │      │
│  │  │  Outbound: 5432 to RDS-SG               │     │      │
│  │  │  Outbound: 443 to Internet (NAT)        │     │      │
│  │  └────────────────┬────────────────────────┘     │      │
│  └───────────────────┼───────────────────────────────┘      │
│                      │                                      │
│  ┌───────────────────▼───────────────────────────────┐      │
│  │           Private Subnet (AZ-2)                   │      │
│  │                                                   │      │
│  │  ┌─────────────────────────────────────────┐     │      │
│  │  │  Amazon RDS (PostgreSQL)                │     │      │
│  │  │  Security Group: RDS-SG                 │     │      │
│  │  │  Inbound: 5432 from ECS-SG              │     │      │
│  │  │  Outbound: None                         │     │      │
│  │  └─────────────────────────────────────────┘     │      │
│  └───────────────────────────────────────────────────┘      │
│                                                             │
│  ┌──────────────────────────────────────────────────┐      │
│  │              NAT Gateway                         │      │
│  │  (For ECS to access AWS Services)                │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```


## 12. Suggestion Engine Logic Flow

```
                    START
                      │
                      ▼
            ┌─────────────────┐
            │ Receive Context │
            │ - Diagnosis     │
            │ - Symptoms      │
            │ - Patient Info  │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Query Doctor's  │
            │ Past Rx History │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
         ┌──│ Similar Cases   │
         │  │ Found?          │
         │  └────────┬────────┘
         │           │
         │ No        │ Yes
         │           ▼
         │  ┌─────────────────┐
         │  │ Extract Common  │
         │  │ Medications &   │
         │  │ Patterns        │
         │  └────────┬────────┘
         │           │
         │           ▼
         │  ┌─────────────────┐
         │  │ Calculate       │
         │  │ Frequency &     │
         │  │ Confidence      │
         │  └────────┬────────┘
         │           │
         │           └──────────┐
         │                      │
         ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│ Query Standard  │    │ Rank Suggestions│
│ Treatment       │    │ by Confidence   │
│ Guidelines DB   │    └────────┬────────┘
└────────┬────────┘             │
         │                      │
         └──────────────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Apply Filters:  │
            │ - Allergies     │
            │ - Interactions  │
            │ - Contraindic.  │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Format Output:  │
            │ - Med Name      │
            │ - Dosage        │
            │ - Frequency     │
            │ - Duration      │
            │ - Instructions  │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Return Top 3-5  │
            │ Suggestions     │
            └────────┬────────┘
                     │
                     ▼
                    END
```



---

## 14. Glossary

- **OPD**: Outpatient Department - clinic setting where patients visit for consultation
- **STT**: Speech-to-Text - technology that converts spoken words to written text
- **NLP**: Natural Language Processing - AI technology for understanding human language
- **JWT**: JSON Web Token - secure method for transmitting information between parties
- **EHR**: Electronic Health Record - digital version of patient medical records
- **EMR**: Electronic Medical Record - similar to EHR, focused on clinical data
- **DISHA**: Digital Information Security in Healthcare Act (India) - healthcare data regulation
- **HIPAA**: Health Insurance Portability and Accountability Act (US) - healthcare privacy law
- **SOAP**: Subjective, Objective, Assessment, Plan - medical note format
- **RDS**: Relational Database Service (AWS) - managed database service
- **ECS**: Elastic Container Service (AWS) - container orchestration service
- **Fargate**: AWS serverless compute engine for containers
- **S3**: Simple Storage Service (AWS) - object storage service
- **VPC**: Virtual Private Cloud (AWS) - isolated cloud network
- **ALB**: Application Load Balancer - distributes incoming traffic
- **ACM**: AWS Certificate Manager - manages SSL/TLS certificates
- **IAM**: Identity and Access Management - AWS security service
- **KMS**: Key Management Service - encryption key management
- **Multi-AZ**: Multiple Availability Zones - high availability deployment
- **CI/CD**: Continuous Integration/Continuous Deployment - automated software delivery
- **API**: Application Programming Interface - software communication protocol
- **PDF**: Portable Document Format - standardized document format
- **HTTPS**: Hypertext Transfer Protocol Secure - encrypted web communication
- **TLS**: Transport Layer Security - cryptographic protocol
- **SQL**: Structured Query Language - database query language
- **ORM**: Object-Relational Mapping - database abstraction layer
- **REST**: Representational State Transfer - API architectural style
- **JSON**: JavaScript Object Notation - data interchange format
- **CORS**: Cross-Origin Resource Sharing - web security mechanism
- **XSS**: Cross-Site Scripting - security vulnerability
- **CSRF**: Cross-Site Request Forgery - security vulnerability
- **MFA**: Multi-Factor Authentication - enhanced security method
- **OTP**: One-Time Password - temporary authentication code
- **PWA**: Progressive Web App - web app with native-like features
- **CDN**: Content Delivery Network - distributed content delivery
- **NAT**: Network Address Translation - IP address mapping
- **WSGI**: Web Server Gateway Interface - Python web server standard
- **SDK**: Software Development Kit - development tools package

---

**Document Version**: 2.0  
**Last Updated**: 2026-02-11  
**Status**: Approved for Development  
**Next Review**: 2026-03-11

---

## Document Navigation

This is the complete requirements and planning document for SEVA Arogya. For detailed technical design and implementation details, refer to **design.md**.

### Quick Links
- Section 1-2: Overview and Architecture
- Section 3: Core Features (detailed requirements)
- Section 5: Non-Functional Requirements (performance, security, etc.)
- Section 6: Technical Requirements (stack and infrastructure)
- Section 7-8: User Stories and Acceptance Criteria
- Section 13: Visual Diagrams (all system diagrams)
- Section 14: Glossary (terminology reference)
