# SEVA Arogya - System Design Document

## Architectural Overview

SEVA Arogya is designed as a cloud-based, low-latency application that leverages managed services to achieve scalability and reliability. The system follows a modular client-server architecture:

- **Frontend:** A web application (React) that handles user interaction, voice recording, and displays structured prescription content.
- **Backend:** A RESTful API (Python Flask) running in Docker containers, responsible for processing voice, structuring data, suggesting content, and generating prescriptions.
- **External AI Services:** AWS services (Transcribe Medical, Comprehend Medical, Translate) are used for speech recognition, natural language processing, and translation, to avoid building these complex components from scratch.
- **Data Storage:** Persistent data is stored securely using AWS cloud services (RDS for relational data, S3 for documents). AWS Cognito handles user authentication and identity management.
- **Infrastructure:** The application is deployed on AWS ECS Fargate with an Application Load Balancer, ensuring easy scaling and no server management. CI/CD and automation are set up to maintain code quality and sync documentation with development.

This design prioritizes **speed** (real-time transcription), **accuracy** (medical-domain optimizations), **security** (patient data protection), and **extensibility** (ability to add features like new languages or integrations later). We choose AWS managed components wherever possible to reduce operational overhead and focus on core application logic.

## Tech Stack and Key Decisions

### Backend Framework: Flask (Python) in Docker

**Rationale:** Flask is lightweight and easy to develop REST APIs with. Python's ecosystem offers strong libraries for machine learning and NLP, which is beneficial for parsing medical text if we augment AWS services. Containerizing the app ensures consistency across development, testing, and production. Python/Flask is a good fit for quick prototyping of logic like text processing, and can handle the expected load with proper scaling (each Flask instance can handle multiple concurrent requests behind a load balancer).

### Frontend Framework: React (JavaScript)

**Rationale:** React allows us to create a dynamic, responsive UI that can handle real-time updates (like streaming text, suggestion pop-ups) smoothly. It has a rich ecosystem for state management (Redux or Context API) which will help manage the complex state of the form (voice input, structured fields, edits). Additionally, React can be built and deployed as static files (served from S3/CloudFront or via Flask), making deployment flexible. Using a modern web app ensures cross-device compatibility (just need a browser) without installing native apps initially.

### Speech-to-Text Engine: Amazon Transcribe Medical (AWS)

**Rationale:** Amazon Transcribe Medical is a cloud service specialized for medical speech recognition, including support for medical vocabulary and (importantly) Indian English accent and possibly Hindi (if not, we might constrain voice input to English initially). Offloading STT to AWS ensures high accuracy out-of-the-box and reduces development time. It also scales automatically to multiple concurrent transcription sessions. Alternative considered: Google Cloud STT or offline models like Vosk; but tight AWS integration and known medical tuning tipped the decision to Transcribe Medical.

### NLP for Structuring: Amazon Comprehend Medical and Custom Rules

**Rationale:** Amazon Comprehend Medical can identify medical entities (symptoms, medications, anatomy, test results) from unstructured text. Using it means we get a baseline of structured data extraction without developing a full NLP pipeline from scratch. We will likely combine Comprehend's output with some custom logic (for example, Comprehend might identify a drug name and dosage, but we need to map that into our prescription fields explicitly). If Comprehend Medical lacks support for local language input or certain Indian context, we have the flexibility to integrate a custom parser or add vocabulary. The system can fall back to a simpler keyword-based extraction for unsupported cases or use translation (e.g., transcribe Hindi speech to text, then translate to English for Comprehend to parse).

### Suggestions Engine: Custom Python Module (ML/Rule-based)

**Rationale:** Suggestions need to be tailored per doctor and evolve over time. We design this as a separate service layer in the backend that can start simple (rule-based suggestions from a dictionary of conditions-to-medications, and user's own history) and later incorporate machine learning (like collaborative filtering or a small neural model that recommends based on context and past data). Keeping it custom allows using the doctor's data (which we store) in a controlled way. Initially, we might not use an AWS service for this because it's quite specific (Amazon does not provide a "prescription suggestion" API out-of-the-box). Instead, we may leverage a local database of drugs and some logic. This module is loosely coupled so it could call external APIs or models in the future if needed (for example, a cloud service that provides clinical decision support).

### Database: Amazon RDS - PostgreSQL

**Rationale:** We need to store structured data like prescriptions, user profiles, and potentially a list of medications or usage statistics. A relational database fits well because:
- Prescriptions can be represented with relations (Doctor table, Prescription table, Medication entries table etc.), enabling SQL queries (e.g., count how many times a drug was prescribed, retrieve all prescriptions of a patient if we add that feature, etc.)
- PostgreSQL is reliable, widely used, and has support for JSON fields if we need semi-structured data
- Amazon RDS is managed, so backups, replication, failover are handled by AWS, aligning with our low-ops approach. We can start with a small instance and scale vertically or horizontally (read replicas) as needed
- Security group settings and VPC placement will ensure the DB is not exposed publicly, only accessed by the app

### File Storage: Amazon S3 (Simple Storage Service)

**Rationale:** S3 will be used to store generated prescription PDFs and possibly any uploaded content (if in future doctors attach images or if we decide to save audio files for audit). S3 provides virtually infinite storage, high durability, and easy integration for downloading files. For example, after generating a PDF, we can either return it directly or store it in S3 and give the client a pre-signed URL for download. S3 is also useful for hosting the front-end (React build) as a static website, which can be served via a CDN. It's cost-effective and simplifies file management compared to storing files in the DB.

### Authentication & User Management: Amazon Cognito

**Rationale:** Cognito User Pools offer a ready-to-use, secure authentication service supporting features like sign-up, email/phone verification, multi-factor auth, and JWT token issuance. This saves us from implementing our own user authentication logic (which is error-prone and time-consuming to secure). Cognito can integrate with our front-end through SDK or OAuth flows, and the backend can validate Cognito's tokens to secure API endpoints. It also allows easy management of user attributes (we can store some profile info in Cognito or just an ID to reference our DB). This choice also positions us well for scaling (Cognito can handle large numbers of users) and compliance (Cognito has advanced security features we can opt into).

### Deployment Platform: AWS ECS Fargate (Docker containers)

**Rationale:** Fargate is a serverless container platform, meaning we don't manage EC2 instances or OS patches. We define our container (with Flask and possibly Gunicorn for concurrency) and ECS will run it as tasks. It can auto-scale the number of task instances based on CPU/Mem usage or request rates (possible integration with Application Load Balancer request count). This fits our requirement to handle variable load and scale to zero (or a minimal level) when idle to save cost. We also considered AWS Lambda for the backend (serverless functions). While Lambda could work for short tasks (transcription requests), the overall app has multiple endpoints and would benefit from in-memory caching between requests (e.g., keep a loaded suggestion model or an initialized connection to DB). A container service gives us more flexibility in that regard. Fargate also easily sits behind an ALB to expose a stable HTTPS endpoint.

### API Gateway vs ALB: Application Load Balancer (ALB)

**Rationale:** Since we are already using Fargate (ECS), an ALB is the straightforward way to distribute traffic to the container tasks. ALB supports path-based routing, health checks, and TLS termination. API Gateway is more often used for Lambda or microservices; it adds features like request validation, rate limiting, etc., but for our use case, ALB + Flask is sufficient and simpler. We will implement any needed request validation in Flask or via a middleware. ALB also allows WebSocket or streaming support if we need it later for real-time transcription.

### PDF Generation: Python Library (ReportLab or WeasyPrint)

**Rationale:** Generating a PDF on the fly when a prescription is finalized keeps the flow simple (no extra service needed). Python has libraries to create PDFs or even HTML-to-PDF converters which can style a document easily. We'll likely create a template (maybe using an HTML/CSS template for the prescription layout) and render it with patient/doctor data. WeasyPrint (HTML to PDF) or ReportLab (drawing PDF with Python) are potential choices. This approach means the PDF bytes are produced in-memory and can be returned to the client or stored. It also means if we want to change the format or add a logo, we just adjust the template and code accordingly.

### Translation: Amazon Translate

**Rationale:** To generate prescriptions in local languages, we can leverage Amazon Translate for translating the structured text (like instructions or diagnoses). It supports Hindi and many other languages. While medical context translation might not be perfect, we can combine it with a curated dictionary approach. For example, we might translate general sentences but ensure certain terms remain unchanged or use a custom glossary (AWS Translate allows custom terminology lists). This is far easier than building our own translation engine. Alternatively, if we find translation quality issues, we could implement a simpler approach: maintain a bilingual dictionary for common phrases (like "twice daily" -> "दिन में दो बार") and just substitute those, but that covers only limited cases. Using Amazon Translate gives broad coverage with minimal dev effort, and we can improve it iteratively.

### Infrastructure as Code: AWS CloudFormation or Terraform

**Rationale:** We want a reproducible deployment. Using IaC means we can version control the AWS resource setup. We'll likely define resources like ECS Task Definition, Service, ALB, RDS, S3 buckets, Cognito user pool, etc., in code form. This also makes environment creation (dev/staging/prod) easier and reduces manual configuration errors. For now, it might be partly manual or using AWS console for initial prototype, but moving to IaC is intended as the project grows.

### CI/CD Pipeline: GitHub Actions or AWS CodePipeline

**Rationale:** Automating build, test, and deploy steps ensures we can deliver updates quickly and reliably. A pipeline will lint the code (using Black, Flake8 for Python and ESLint for JS), run tests, build the Docker image, and deploy to a Fargate service (or update tasks). We favor GitHub Actions due to ease of integration with GitHub repo, but CodePipeline is also an option (especially if we want to keep everything on AWS). This pipeline will also be configured to generate/update documentation if certain changes are detected.

### Monitoring & Logging: AWS CloudWatch & X-Ray

**Rationale:** CloudWatch will aggregate logs from the Flask app (via log drivers) and can track metrics like number of requests, latency, memory/CPU of containers, etc. We will set up CloudWatch Alarms for critical conditions (e.g., high error rate or high latency in transcriptions). Additionally, we may use AWS X-Ray to trace requests through our application, especially if we want insight into performance of external calls (Transcribe API call duration, etc.). This helps identify bottlenecks (for example, if transcription is slow, or if DB queries are taking time). Monitoring is vital for a production clinical tool to ensure it's performing as expected.

### Security & Secrets: AWS Secrets Manager and IAM

**Rationale:** We will store sensitive configuration like database credentials or API keys (if any external) in Secrets Manager. The Flask app can retrieve these at startup (with proper IAM permissions). This avoids hardcoding secrets in code or config files. IAM roles will be used extensively to grant least-privilege access:
- The ECS task running our backend gets an IAM role permitting it to call only specific AWS services (Transcribe, Comprehend, Translate, S3 on certain bucket, etc.)
- The Cognito user pool will manage user auth, but if needed, an Identity Pool could grant temporary AWS credentials to front-end for direct S3 access (not likely needed for this app, except maybe if we allow direct S3 upload of audio or download of PDF)
- By using IAM roles and not embedding AWS creds, we enhance security (nothing sensitive on the client or in code)

### Region and Localization: AWS ap-south-1 (Mumbai)

**Rationale:** We will deploy initially in an AWS region in India (such as ap-south-1 (Mumbai)) to keep latency low for Indian users and to ensure data residency in India. Placing resources in Mumbai region reduces round-trip time for API calls (especially since audio data streaming can be sensitive to latency). Also, keeping health data in-country aligns with anticipated regulatory preferences (DISHA likely will encourage local storage of health data). We'll verify that the AWS services we need (Transcribe Medical, Comprehend Medical) are available in Mumbai; if not, we might use another closest region (Singapore) with careful consideration of latency and data compliance.

## System Architecture Description

### Web Client (React App)

Runs in the doctor's browser. It provides:

- **Login Interface:** where doctors authenticate via Cognito (could be an embedded form or redirect to Cognito-hosted UI)
- **Voice Recording Module:** using the Web Audio API. The UI has a record button which, when pressed, starts capturing audio (possibly showing a waveform or listening indicator) and when released (or toggled off), stops and prepares the audio for upload
- **Dynamic Prescription Form:** as the doctor speaks, transcribed text and identified fields appear here. This form is essentially the digital equivalent of a prescription pad, with sections for each type of information. The doctor can also type in it
- **Suggestions Dropdowns:** for fields like medication, when the system has suggestions, the UI might show a dropdown or autocomplete list
- **Preview & Finalize View:** a preview of the prescription in the final formatted style. The doctor can review and then confirm to finalize
- **Networking:** the app communicates with the backend via HTTPS calls (using fetch or Axios). It handles responses for transcription, suggestions, and can fetch or post data for any saved info
- **State Management:** likely uses local state or context to keep track of the current prescription data structure (symptoms list, medications list etc.), updating it as results come in or user edits occur
- **Mobile/Tablet Consideration:** Though not a separate component, note that the web app is responsive and can run on a tablet for portability in clinic. We might package it as a PWA in future so that it can work more seamlessly on mobile devices with microphone access

### Authentication & Authorization (Amazon Cognito)

**Amazon Cognito** manages user authentication. We set up:

- A **Cognito User Pool** for doctors with fields (username, email, etc.). It handles user sign-up (with verification email/SMS if configured), login, and can enforce password policies
- Cognito provides a hosted authentication flow or tokens for custom UI. In our case, we likely use the Cognito JavaScript SDK to sign in and obtain a **JWT access token**
- The React app then includes this JWT in the Authorization header for API calls to our backend
- The backend has a middleware or filter that validates incoming JWTs (by checking signature against Cognito's public keys and ensuring token not expired and correct audience). We can use a library or AWS provided middleware for JWT verification
- Once validated, the backend knows the user's identity (their Cognito user id or email). We map that to our internal user records (we may use Cognito's user id as primary key or store a separate user table in RDS linked via email/username)
- **Authorization**: At this stage, our app is single-tenant per doctor (each doctor only accesses their own data). So authorization is mainly ensuring the user is authenticated and then scoping DB queries to that user. There isn't a role hierarchy now (like admin vs user), except possibly in future for an admin user to see usage stats

### API Backend (Flask Application)

The Flask app exposes various REST endpoints (all secured with auth). It's stateless (does not store session data on server side; relies on JWT for user context). Key endpoints and internal flows:

#### POST /transcribe
Accepts audio data. Upon call:
- The Flask handler receives the audio file (likely as part of form-data or binary stream)
- It verifies the JWT, identifies the user (e.g., user_id)
- It calls the Amazon Transcribe Medical API. For short audio, it could use the synchronous API
- Once transcription is obtained (text + maybe confidence metadata), the Flask app may optionally call Comprehend Medical to parse it
- The Flask app returns a JSON response like `{ "text": "...", "entities": [...] }` or directly structured data

#### POST /analyze (optional)
If we separate steps, this could take raw text and return structured data and suggestions. However, combining into /transcribe might be more efficient (transcribe then analyze immediately).

#### GET /suggest
Returns suggestions for the current context (like current diagnosis or partial med input). Could also be that suggestions are included in /analyze output to reduce calls.

#### POST /prescriptions
Save or finalize prescription:
- Expects a JSON of the structured prescription (patient info, list of meds, etc.) from the front-end when the doctor clicks finalize
- The backend will create a record in the database (Prescription table, Medications sub-table etc.), linking it with the user's ID
- It then generates a PDF. If quick, it can generate on the fly and send back the PDF bytes in the response (with appropriate headers for download)
- Possibly also returns a confirmation or any additional info (like "prescription saved with ID 123")

#### GET /prescriptions
If doctors can view past prescriptions, these endpoints would retrieve data. Not a priority now, but we design DB with that in mind.

#### PUT /profile and GET /profile
To update or fetch doctor's profile settings (like preferred language, etc.). On sign-up, some profile info is set; they can change it later.

**Internal Structure:** Within the Flask app, we might organize code into blueprints or modules:
- auth.py (maybe not needed if using pure Cognito JWT, but might have utility methods for auth)
- transcription.py (functions to call Transcribe API)
- nlp.py (functions to call Comprehend or do parsing)
- suggestion.py (logic for suggestions)
- pdf.py (template or PDF generation code)
- models.py or DB access layer (SQLAlchemy models or plain SQL queries)

We can use SQLAlchemy as an ORM for ease of interacting with PostgreSQL, or use raw queries for simplicity. SQLAlchemy would map to tables: Doctor, Prescription, Medication, etc., and allow Pythonic queries.

**Error Handling:** The API will consistently return structured errors. For example, if Transcribe fails, it might return JSON `{ "error": "Transcription failed, please retry." }` with a 500 status. The front-end will handle these gracefully.

### AWS Transcribe (Medical)

This is an external service, but integral to our flow:
- We configure Transcribe for our use via AWS SDK (boto3). For medical transcription, we specify the domain (medical) and the language (e.g., en-IN for English (Indian) medical, if available)
- The output of Transcribe includes text and possibly punctuation. We might handle punctuation insertion if needed
- We do not permanently store the raw audio on our side (unless we choose to save for analysis). The audio is sent to Transcribe and we get text

### AWS Comprehend Medical (NLP)

Usage in our system:
- Input: the transcribed text of one segment or the whole compiled text
- Comprehend Medical returns entities with types (MEDICATION, DOSAGE, SYMPTOM, etc.), and also relationship info (it might link a dosage to a medication name, etc.)
- We will parse this result to fill our data structure
- For languages: Comprehend Medical at present mainly supports English. So if the doctor speaks in Hindi, one strategy is to use AWS Transcribe (Hindi) to get text, then use a translation (Hindi->English), then Comprehend on English, then translate output back to Hindi if needed for display

### AWS Translate (for output)

When the doctor requests the prescription in a different language:
- We gather the structured text that needs translation. We will not translate certain fields like drug names or numerical values
- We call Amazon Translate for each text field or a concatenated block of text
- We can provide a custom terminology to Translate to ensure certain terms remain in English or are replaced with desired translations
- The translated text is then placed into the PDF template instead of the English text
- If translation fails (e.g., network issue), we fall back to English as a safe default and possibly notify the user

### Database (AWS RDS - Postgres) Schema Design

We propose a schema roughly as:

- **Doctors**: (doctor_id PK, name, email, password_hash if not using Cognito for password, or Cognito_sub, preferred_language, clinic_name, etc.)
- **Prescriptions**: (prescription_id PK, doctor_id FK, patient_name, patient_age, date, diagnosis_text, instructions_text, language, created_at timestamp, etc.)
- **Prescription_Meds**: (prescription_id FK, med_name, dosage, frequency, duration, additional_note). One row per medication in a prescription
- **Medications Master**: (med_name PK, perhaps mapping to generic name or category). This could be a reference list of common medications for suggestions and validation
- **Audit log**: Possibly a simple table (log_id, doctor_id, action, timestamp, details) to record events like "login", "created prescription #X", etc.

All data in RDS will be in a private subnet, accessible by the backend only. We'll enable encryption at rest on the RDS and enforce SSL connections from the app.

### File Storage & Static Content

- **Prescription PDFs:** We may decide to store each finalized prescription PDF in S3 for persistence, naming the file by prescription_id or a UID. This is useful if the doctor wants to re-download a past prescription
- **S3 Bucket setup:** likely one bucket, with folders like /prescriptions/{doctor_id}/{prescription_id}.pdf. Access: either private (backend uses IAM to fetch if needed) or if we want direct access, use pre-signed URLs
- **Static Frontend:** If we deploy the React app to S3 as a static site, we'd have another bucket (or subfolder) that hosts the HTML/JS/CSS. That would be tied to a CloudFront distribution for CDN
- **Audio Files:** By default we won't store audio to avoid heavy storage and privacy issues

### Application Load Balancer (ALB)

- We'll set up an ALB to listen on port 443 (HTTPS) for our domain. It holds an SSL certificate (from AWS Certificate Manager) for encrypting traffic
- The ALB has a target group pointing to the ECS Fargate tasks (Flask containers). Health checks will be configured (Flask might have a /health endpoint responding with 200 OK)
- The ALB routes all requests on relevant paths (maybe all /api/*) to the backend
- ALB provides basic DDOS protection and can scale to handle a large number of connections
- If we use WebSockets later (for streaming voice), ALB supports WebSocket pass-through

### Network Security & VPC

- All AWS components will reside in a VPC (Virtual Private Cloud). We will use private subnets for ECS tasks and RDS. The ALB can be in a public subnet but only exposes port 443
- The ECS tasks (Flask containers) need outbound internet access to call AWS APIs (Transcribe etc.), so they will use a NAT Gateway or have public IP with security group
- Security Groups:
  - ALB SG: allows inbound 443 from the internet, outbound to ECS SG
  - ECS SG: allows inbound from ALB SG on whatever port the container listens (e.g., 5000 or 80), and outbound to RDS SG on port 5432, and outbound to internet (for AWS API calls)
  - RDS SG: allows inbound from ECS SG on 5432 (Postgres)
- This setup ensures the database is not accessible from the internet, and only our app server can talk to it

### Scalability Considerations

- ECS tasks (Flask app) can scale out horizontally. We can configure auto-scaling based on CPU or memory usage, or based on request rate
- AWS Transcribe and other services scale on their end (they handle concurrent requests transparently up to service limits)
- The database can scale read capacity via read replicas and write by instance size
- We ensure statelessness so any app server can handle any user's request. Session is via JWT
- We might use caching for suggestions or drug list lookup to reduce DB hits (e.g., cache common suggestion results in memory or an ElastiCache Redis if needed)

## Data Flow

### 1. User Login
When a doctor navigates to the application, they either sign in or sign up. Using Cognito's hosted UI (or an embedded widget), they enter credentials. Cognito verifies them and redirects back to the app with a token. Now the user is authenticated with a JWT stored in the app.

### 2. Start Consultation (UI ready)
The doctor opens a new prescription on the UI (this could be just the default state after login - an empty form is ready). They can enter patient details (either manually type name/age or perhaps select an existing patient if that was in scope, but MVP might just type each time). The app is now ready to record notes.

### 3. Voice Dictation (Frontend capture)
The doctor presses the "Record" button and speaks a sentence or two. The front-end, via the microphone, captures audio. Because continuous streaming is complex, we assume the doctor presses "Stop" after that sentence or it auto-stops after a few seconds of silence.

### 4. Sending Audio (API call)
The captured audio blob is then sent via an HTTP POST to the backend API endpoint (e.g., POST /transcribe). The JWT token is included in headers for auth. The payload is binary (the audio file data).

### 5. Speech-to-Text Processing
The Flask backend receives the request:
- Auth middleware checks the JWT, confirms the user
- The audio data is saved to memory or a temp file. The backend calls AWS Transcribe
- Transcribe returns text
- The backend takes that text and optionally calls Comprehend Medical
- Comprehend analyzes and might return entities
- The backend maps these to structured fields
- The backend also calls the suggestion engine
- The backend responds with JSON containing transcript, structured data, and suggestions

### 6. Frontend Update
The React app receives the response:
- It displays the transcribed text
- It also updates the structured fields UI
- If suggestions were present, they appear as highlighted options
- The doctor can correct anything if needed

### 7. Subsequent Dictations
The doctor continues, perhaps now saying a diagnosis or plan. The same process repeats: audio -> /transcribe -> text -> structure. Response goes back, and frontend updates with new information.

### 8. Finalize Prescription
After dictating all parts and reviewing, the doctor clicks "Finalize":
- The front-end compiles the current structured data and sends a POST /prescriptions request
- The backend authenticates, validates the data
- Creates a new prescription record in the database
- Calls the PDF generation module
- If output language != English, translates certain fields before generating PDF
- The PDF binary is either directly returned or saved to S3
- The backend returns a success response

### 9. Prescription Delivery
The front-end triggers the print or download. The doctor hands the printed sheet to the patient or shares it electronically.

### 10. Post-Finalization
- The app might reset to a new blank prescription screen for the next patient
- The structured data is now saved server-side
- The suggestions engine can update its learning based on this new prescription

### 11. Logout or Session End
At the end of the shift, the doctor logs out from the app, which simply clears tokens. All data remains saved for future, accessible upon next login.

## Frontend and Backend Interaction Details

### Login Integration
The front-end uses AWS Amplify or the AWS Cognito SDK. After the user enters credentials, the Cognito service returns tokens (Access Token, ID Token, Refresh Token). All subsequent API calls from frontend include the **Authorization: Bearer <token>** header. The backend has a middleware that checks this token using Cognito's JSON Web Key Set (JWKS) to verify the signature.

### State Management on Frontend
The React app likely has a context or Redux store for the "current prescription". Each voice input cycle updates this state. For example, there might be actions: ADD_SYMPTOM, SET_DIAGNOSIS, ADD_MED, etc., that the responses from backend trigger.

### CORS
If the frontend is hosted on a different domain, we will enable CORS on the Flask app for the allowed origin. For simplicity, if served from same domain (maybe we serve React via Flask), then CORS isn't an issue.

### Front-end Error Handling
- If a token expires, the front-end should handle a 401 response by refreshing the token or forcing re-login
- For expected errors, the backend returns a 4xx code with a message; the front-end can display that message
- Network issues: the front-end should detect if the request times out and prompt "Network error, please check connection"
- Audio permission issues: If the user hasn't given microphone permission, the app should prompt them

### Session Persistence
It's convenient for doctors if they don't have to log in every single time during the day. So we will implement session persistence via Cognito's refresh token. The front-end can quietly use the refresh token to get a new Access token when needed.

### Using the Microphone API
On pressing record, we use navigator.mediaDevices.getUserMedia({ audio: true }) to get a stream. Then a MediaRecorder to record audio. We must decide format: Amazon Transcribe expects specific audio format (PCM 16kHz, mono, for example).

## Security Considerations

Security is critical since we are dealing with healthcare data. The design incorporates security at multiple levels:

### Authentication Security
By leveraging Cognito, we inherit a lot of security features (secure password storage, account lockout for too many failed attempts, etc.). We will enforce TLS everywhere so credentials are not exposed. We also consider enabling MFA in Cognito as an option for doctors who want extra security.

### Authorization Checks
Every API endpoint will confirm the identity from JWT and then check any relevant permissions. For now, the rule is simple: users can only act on resources they own (their prescriptions).

### Data Encryption
- At rest: RDS encryption will be enabled (AES-256 by AWS). S3 encryption enabled for all buckets
- In transit: Enforce SSL for DB connection; all calls to external AWS services from backend use HTTPS by default
- The JWT tokens from Cognito are transmitted over HTTPS and stored client-side; they are short-lived and scoped

### Sensitive Data Minimization
We intentionally do not collect or store more patient data than necessary. At MVP, we might only have patient name/age on the prescription. The voice recordings are not stored persistently.

### Audit Logging
We keep logs of actions which can be used to trace any security incidents. CloudWatch logs will show each API call with user id.

### Preventing Unauthorized Access
The combination of JWT auth and DB scoping ensures one user can't retrieve another's data through the API. Additionally, the S3 structure will use random IDs or user-specific paths so one user can't guess another's PDF link.

### Web App Security
- Use HTTPS only. Possibly HSTS header for our domain
- Protect against XSS by not injecting any user-generated content into pages unsanitized
- Protect against CSRF: Since we use JWT and not cookies for auth, CSRF is less of an issue
- Content Security Policy (CSP) headers can be added to ALB or CloudFront

### Secrets & Config
No secret keys will be in the front-end code. The back-end will not have hard-coded secrets either; everything is fetched from environment or Secrets Manager at runtime.

### Compliance Alignment
- **DISHA (India's health data bill)** likely will require explicit patient consent for data use. In our design, since patients aren't directly using the system, the doctor is the one inputting data
- **HIPAA** (if ever relevant): our use of encryption, access control, audit logs are steps in the right direction

### Rate Limiting & Abuse
Because this is a closed system for authorized doctors, we may not implement strict rate limiting initially. But to be safe, the backend could enforce limits like: no more than X transcription requests per minute per user.

### Backup and Recovery
RDS will have automated backups. S3 is inherently durable. We will also periodically export critical data or have multi-AZ RDS to handle instance failure.

## AWS Resources Breakdown

### Amazon Cognito User Pool
Manages user registration, login, and tokens. Configured with a domain for hosted UI or integrated via SDK. Provides JWTs that our app uses for auth.

### Amazon ECS (Fargate) Cluster
Runs our Dockerized Flask backend. We define a Task Definition with containers. Fargate Service ensures the desired number of tasks are running and handles deploying new versions.

### Amazon Elastic Load Balancer (Application Load Balancer)
Fronts the Fargate service. Listens on HTTPS, uses an ACM certificate for our app's domain. Health-checks the tasks and routes traffic.

### Amazon RDS (PostgreSQL)
Stores persistent data (users, prescriptions, etc.). Configured with multi-AZ (for HA) if desired, and automated backups.

### Amazon S3
- Bucket 1: seva-arogya-prescriptions (private) for storing PDFs
- Bucket 2: seva-arogya-web (public for static hosting) if we host the front-end separately

### Amazon CloudFront
If using static bucket, a CloudFront distribution will cache the static content for global access and provide HTTPS on the front-end site.

### AWS Transcribe (Medical)
No infrastructure to provision; we simply call this service via its API. We might configure a custom vocabulary within Transcribe if needed.

### AWS Comprehend Medical
Similarly called on demand, no infra setup. Ensure the IAM role has permission comprehendmedical:DetectEntities.

### AWS Translate
Called on demand. Possibly ensure the target languages are supported. No infra needed except IAM permission translate:TranslateText.

### AWS Secrets Manager
We will store e.g., DB_PASSWORD and perhaps any other secret. Our ECS task role must have permission to read these specific secrets.

### Amazon CloudWatch
- Logs: We configure the ECS task to send logs to CloudWatch Logs
- Metrics: By default, CPU/Memory of ECS, and RDS performance, etc., are available
- Alarms: e.g., an alarm if CPU > 80% for 5 minutes

### AWS X-Ray (Optional)
We can enable X-Ray tracing in the Flask app. This will give a service map and traces through our code and external calls.

### AWS Identity and Access Management (IAM)
Key roles/policies:
- ECS Task Execution Role: Allows ECS to pull images from ECR, log to CloudWatch
- ECS Task Role: Attached to running container for AWS API calls

### Amazon Elastic Container Registry (ECR)
We will use ECR to store our Docker image for the backend. The CI/CD will push to ECR and ECS will fetch from there.

## DevOps and Automation Hooks

To ensure high code quality and that our documentation remains up-to-date with the system, we implement several automation hooks in our development workflow:

### Linting & Formatting Checks
Our CI pipeline runs linters for both backend and frontend. For Python, we use Black (auto-formatter) and Flake8 (style and error check). For React/JS, we use ESLint and Prettier. These tools enforce a consistent code style and catch common errors.

### Automated Testing in CI
We maintain a test suite:
- **Unit Tests:** test the parsing logic, test suggestion logic, test utility functions
- **Integration Tests:** spin up a test instance of the Flask app, simulate a JWT, and call endpoints with sample data
- **End-to-End Tests:** In a staging environment, we could have a script that runs a headless browser to simulate a user login, record a sample, and go through to PDF generation

### Voice-to-Text Accuracy Monitoring
We schedule a periodic job to run a set of sample audio clips through the transcription and structuring pipeline. These sample audios have known "ground truth" transcriptions and expected structured outputs. The job will compare actual results to expected and log an accuracy metric.

### Documentation Sync (Design & Requirements)
We treat requirements.md and design.md as living documents. To avoid them getting outdated:
- We create a commit hook or CI job that checks for certain changes
- In the future, we might integrate an AI assistant (like Kiro itself) to auto-scan differences

### Continuous Deployment Hooks
After tests pass, the pipeline automatically deploys to a dev/test environment. We might require manual approval for deploying to production. The pipeline also invalidates CloudFront cache if front-end changed, runs DB migrations if any.

### Monitoring & Alerts Setup
We integrate alerts such that if certain alarms trigger (e.g., high error rate or system down) an email or message is sent to the dev team.

### Developer Environment
We ensure that the project is easy to spin up for development: maybe a Docker Compose file to run a local Postgres and a local dev server, scripts to add a test user etc.

### Agent (Kiro) Integration
Since Kiro is generating these docs, we consider using it in future development phases. For example, if we have a user story change, a developer or PM could prompt Kiro with the new info and have it update the requirements.md.

By implementing these hooks and processes, we aim for a maintainable, high-quality codebase where the documentation, code, and infrastructure all evolve together systematically.
