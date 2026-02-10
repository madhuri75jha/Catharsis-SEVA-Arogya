# SEVA Arogya - System Diagrams

## 1. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SEVA Arogya System                             │
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
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │  Auth      │  │Transcription│  │ Suggestion │           │
│  │  Module    │  │   Module    │  │   Engine   │           │
│  └────────────┘  └────────────┘  └────────────┘           │
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │    NLP     │  │    PDF     │  │  Database  │           │
│  │  Module    │  │ Generator  │  │   Access   │           │
│  └────────────┘  └────────────┘  └────────────┘           │
└──────────┬───────────────────────────────────┬─────────────┘
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
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  AWS Transcribe  │  │ AWS Comprehend   │               │
│  │    Medical       │  │    Medical       │               │
│  │                  │  │                  │               │
│  │ - Speech to Text │  │ - Entity Extract │               │
│  │ - Medical Terms  │  │ - Medications    │               │
│  │ - Indian Accent  │  │ - Symptoms       │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  AWS Translate   │  │   AWS Cognito    │               │
│  │                  │  │                  │               │
│  │ - Multi-language │  │ - User Auth      │               │
│  │ - Hindi Support  │  │ - JWT Tokens     │               │
│  └──────────────────┘  └──────────────────┘               │
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
│  2.0 Structure &    │────────▶│  D1: Doctor  │
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
│  5.0 Generate PDF   │────────▶│D3: Prescription│
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
│  │                                                              │    │
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

