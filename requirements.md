# SEVA Arogya - Requirements Document

## 1. Executive Summary

SEVA Arogya is a voice-enabled clinical note capture and prescription generation system designed specifically for Indian healthcare settings. The system enables doctors to dictate clinical notes, automatically structures them into prescriptions, and generates professional, multi-language prescription documents. This solution addresses the critical need for faster, more accurate prescription generation in busy OPD (Outpatient Department) environments.

## 2. System Overview

### 2.1 Purpose
To provide doctors with an AI-powered voice assistant that:
- Reduces prescription writing time by 70%
- Eliminates handwriting legibility issues
- Supports multiple Indian languages
- Maintains medical accuracy and compliance
- Integrates seamlessly into existing clinical workflows

### 2.2 Target Users
- **Primary**: Doctors in OPD settings (clinics, hospitals)
- **Secondary**: Patients receiving prescriptions
- **Future**: Clinic administrators, healthcare systems

### 2.3 Key Differentiators
- Medical-domain optimized speech recognition
- Indian accent and terminology support
- Context-aware medication suggestions
- Multi-language prescription output
- Cloud-based, scalable architecture

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
- 90% overall transcription accuracy
- 98% accuracy for common medical terms (100+ term test set)
- 2-second maximum latency from speech end to text display
- Handle 20 short dictations per minute per user
- Graceful handling of background noise

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
- 90% field population accuracy (9/10 test prescriptions)
- All dictated information preserved (no data loss)
- Correct categorization of medications vs instructions
- Support for complex medical sentences
- Manual override capability without data loss


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
- 80% suggestion relevance (8/10 test scenarios)
- Non-intrusive UI (user feedback validation)
- Adaptive learning (Drug A becomes top suggestion after 5 uses)
- Optional toggle to disable suggestions
- Response time < 500ms for suggestion generation

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
- Accurate Hindi translation (4/5 prescriptions validated by bilingual expert)
- Medical terms remain unchanged
- Proper Hindi script rendering in PDF
- Grammar and spelling correctness
- Fallback to English on translation failure

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
- Successful registration and login flow
- Password hashing (bcrypt or similar)
- JWT token validation on all API calls
- 401 error for invalid/expired tokens
- Profile updates persist correctly
- No cross-doctor data access


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
- All structured fields appear in PDF
- Consistent formatting across prescriptions
- Font size ≥ 11pt for body text
- Clear medication table layout
- PDF generation < 3 seconds
- File size < 200KB per prescription
- Print-ready output (no cut-off sections)

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

## 13. Glossary

- **OPD**: Outpatient Department
- **STT**: Speech-to-Text
- **NLP**: Natural Language Processing
- **JWT**: JSON Web Token
- **EHR**: Electronic Health Record
- **DISHA**: Digital Information Security in Healthcare Act (India)
- **HIPAA**: Health Insurance Portability and Accountability Act (US)
- **SOAP**: Subjective, Objective, Assessment, Plan (medical note format)
- **RDS**: Relational Database Service (AWS)
- **ECS**: Elastic Container Service (AWS)
- **S3**: Simple Storage Service (AWS)
- **VPC**: Virtual Private Cloud (AWS)

## 14. References

- [diagrams.md](diagrams.md) - System architecture and flow diagrams
- [Readme.md](Readme.md) - System overview and technical details
- [design.md](design.md) - Detailed system design document
- AWS Transcribe Medical Documentation
- AWS Comprehend Medical Documentation
- DISHA Guidelines (when published)

---

**Document Version**: 2.0  
**Last Updated**: 2026-02-11  
**Status**: Approved for Development
