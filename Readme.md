# 🏥 SEVA Arogya
## Voice-Enabled Clinical Prescription System

> Transform doctor-patient consultations into professional prescriptions using AI-powered voice recognition

[![AWS](https://img.shields.io/badge/AWS-Cloud%20Native-orange)](https://aws.amazon.com)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13%2B-blue)](https://postgresql.org)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- AWS Account with configured credentials
- PostgreSQL (local) or AWS RDS

### 3-Step Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your AWS credentials

# 3. Run the application
python app.py
```

**Access at:** http://localhost:5000

### 🔐 Demo Credentials
- Doctor: `doctor@hospital.com` / `password123`
- Admin: `admin@seva.com` / `admin123`

---

## 🏗️ System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        A[👨‍⚕️ Doctor Browser<br/>React SPA]
    end
    
    subgraph "AWS Cloud"
        subgraph "Edge & Gateway"
            B[☁️ CloudFront CDN]
            C[⚖️ Application Load Balancer]
        end
        
        subgraph "Application Layer"
            D[🐳 ECS Fargate<br/>Flask Backend]
        end
        
        subgraph "AI/ML Services"
            E[🎤 Transcribe Medical<br/>Speech-to-Text]
            F[🧠 Comprehend Medical<br/>Entity Extraction]
            G[🌐 Translate<br/>Multi-language]
        end
        
        subgraph "Data Layer"
            H[(🗄️ RDS PostgreSQL<br/>Prescriptions)]
            I[📦 S3 Buckets<br/>Audio & PDFs]
        end
        
        subgraph "Security & Auth"
            J[🔐 Cognito<br/>User Auth]
            K[🔑 Secrets Manager<br/>Credentials]
        end
    end
    
    A -->|HTTPS| B
    B --> C
    C --> D
    D --> E
    D --> F
    D --> G
    D --> H
    D --> I
    D --> J
    D --> K
    
    style A fill:#e1f5ff
    style D fill:#fff3e0
    style H fill:#f3e5f5
    style I fill:#e8f5e9
```

### 5-Layer Architecture

| Layer | Technology | Purpose |
|-------|-----------|---------|
| 🎨 **Presentation** | React 18+ SPA | User interface & voice capture |
| 🚪 **API Gateway** | AWS ALB | Load balancing & SSL termination |
| ⚙️ **Application** | Flask on ECS Fargate | Business logic & orchestration |
| 💾 **Data** | PostgreSQL + S3 | Structured data & file storage |
| 🔌 **Integration** | AWS SDK (Boto3) | AI/ML service integration |

### Core AWS Services

| Service | Purpose | Key Features |
|---------|---------|--------------|
| 🔐 **Cognito** | Authentication | JWT tokens, MFA support |
| 🎤 **Transcribe Medical** | Speech-to-Text | Medical vocabulary, Indian accents |
| 🧠 **Comprehend Medical** | NLP | Entity extraction, medical ontology |
| 📦 **S3** | Storage | Audio files, PDF prescriptions |
| 🗄️ **RDS PostgreSQL** | Database | ACID compliance, Multi-AZ |
| 🔑 **Secrets Manager** | Security | Credential management |

---

## ✨ Features

### 🎯 Core Capabilities

```mermaid
graph LR
    A[🎤 Voice Input] --> B[📝 Transcription]
    B --> C[🧠 AI Analysis]
    C --> D[💊 Smart Suggestions]
    D --> E[📄 Prescription PDF]
    
    style A fill:#e3f2fd
    style B fill:#f3e5f5
    style C fill:#fff3e0
    style D fill:#e8f5e9
    style E fill:#fce4ec
```

| Feature | Status | Description |
|---------|--------|-------------|
| 🔐 **User Authentication** | ✅ Live | AWS Cognito with JWT tokens |
| 🎤 **Voice Capture** | ✅ Live | Real-time audio recording |
| 📝 **Medical Transcription** | ✅ Live | AWS Transcribe Medical |
| 🧠 **Entity Extraction** | ✅ Live | Medications, symptoms, diagnoses |
| 💊 **Smart Suggestions** | ✅ Live | Context-aware recommendations |
| 📄 **PDF Generation** | ✅ Live | Professional prescription documents |
| 🌐 **Multi-language** | ✅ Live | English & Hindi support |
| 🔄 **Live Streaming** | ✅ Live | Real-time transcription streaming |

### 📱 User Interface

```mermaid
graph LR
    A[🔐 Login] --> B[🏠 Home]
    B --> C[🎤 Transcription]
    C --> D[📋 Review]
    D --> E[📄 Final Prescription]
    E -.-> B
    
    style A fill:#ffebee
    style B fill:#e8f5e9
    style C fill:#e3f2fd
    style D fill:#fff3e0
    style E fill:#f3e5f5
```

1. **Login** (`/login`) - Secure authentication
2. **Home** (`/home`) - Patient search & consultation start
3. **Transcription** (`/transcription`) - Voice capture with live feedback
4. **Final Prescription** (`/final-prescription`) - Review & finalize

---

## 🔌 API Reference

### 🔐 Authentication Endpoints

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant Cog as Cognito
    
    C->>A: POST /api/v1/auth/login
    A->>Cog: Validate credentials
    Cog-->>A: JWT tokens
    A-->>C: Access + Refresh tokens
    
    Note over C,Cog: Token expires after 1 hour
    
    C->>A: POST /api/v1/auth/refresh
    A->>Cog: Validate refresh token
    Cog-->>A: New access token
    A-->>C: New access token
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | User login with email/password |
| `/api/v1/auth/register` | POST | New user registration |
| `/api/v1/auth/verify` | POST | Email verification |
| `/api/v1/auth/logout` | POST | User logout |
| `/api/v1/auth/refresh` | POST | Refresh access token |

### 🎤 Audio & Transcription Endpoints

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant S3 as S3
    participant T as Transcribe
    participant CM as Comprehend
    
    C->>A: POST /api/v1/audio/upload
    A->>S3: Store audio file
    S3-->>A: S3 key
    A-->>C: Upload success
    
    C->>A: POST /api/v1/transcribe
    A->>T: Start transcription job
    T-->>A: Job ID
    A-->>C: Job started
    
    loop Poll status
        C->>A: GET /api/v1/transcribe/status/{job_id}
        A->>T: Check status
        T-->>A: Status
        A-->>C: IN_PROGRESS/COMPLETED
    end
    
    C->>A: GET /api/v1/transcribe/result/{job_id}
    A->>T: Get transcript
    T-->>A: Transcript text
    A->>CM: Extract entities
    CM-->>A: Medical entities
    A-->>C: Transcript + Entities
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/audio/upload` | POST | Upload audio file (MP3/WAV/FLAC) |
| `/api/v1/transcribe` | POST | Start transcription job |
| `/api/v1/transcribe/status/<job_id>` | GET | Check transcription status |
| `/api/v1/transcribe/result/<job_id>` | GET | Get transcript & entities |

### 📄 Prescription Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/prescriptions` | POST | Create new prescription |
| `/api/v1/prescriptions` | GET | List all prescriptions (paginated) |
| `/api/v1/prescriptions/<id>` | GET | Get specific prescription |
| `/api/v1/prescriptions/<id>/download` | GET | Download prescription PDF |

### 🏥 Health & Monitoring

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Basic health check (DB, migrations) |
| `/health/aws-connectivity` | GET | AWS services connectivity check |

---

## ⚙️ Configuration

### 📋 Environment Variables

```bash
# AWS Configuration
AWS_REGION=ap-south-1
AWS_COGNITO_USER_POOL_ID=your-pool-id
AWS_COGNITO_CLIENT_ID=your-client-id
S3_AUDIO_BUCKET=your-audio-bucket
S3_PDF_BUCKET=your-pdf-bucket

# Secrets Manager
DB_SECRET_NAME=seva-arogya/db-credentials
FLASK_SECRET_NAME=seva-arogya/flask-secret
JWT_SECRET_NAME=seva-arogya/jwt-secret

# Database (fallback)
DATABASE_URL=postgresql://user:password@localhost:5432/seva_arogya

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:5000,http://localhost:3000

# Logging
LOG_LEVEL=INFO
```

See `.env.example` for complete configuration template.

### 🔐 AWS Setup Quick Reference

```bash
# Configure AWS CLI
aws configure

# Create Cognito User Pool
aws cognito-idp create-user-pool \
  --pool-name seva-arogya-users \
  --policies "PasswordPolicy={MinimumLength=8}"

# Create S3 Buckets
aws s3 mb s3://seva-arogya-audio-${UNIQUE_ID}
aws s3 mb s3://seva-arogya-pdf-${UNIQUE_ID}

# Create Secrets
aws secretsmanager create-secret \
  --name seva-arogya/db-credentials \
  --secret-string '{"host":"localhost","database":"seva_arogya"}'
```

For detailed AWS setup, see [AWS Setup Guide](#aws-deployment) below.

---

## 🚀 Deployment

### 🏠 Local Development

```bash
# Run application
python app.py

# Run with debug mode
export FLASK_DEBUG=True
export LOG_LEVEL=DEBUG
python app.py

# Run tests
python test_aws_connectivity.py
```

### ☁️ AWS Deployment

```mermaid
graph LR
    A[1️⃣ Pre-Check] --> B[2️⃣ Infrastructure]
    B --> C[3️⃣ Build Image]
    C --> D[4️⃣ Push to ECR]
    D --> E[5️⃣ Update ECS]
    E --> F[6️⃣ Validate]
    
    style A fill:#e3f2fd
    style B fill:#f3e5f5
    style C fill:#fff3e0
    style D fill:#e8f5e9
    style E fill:#fce4ec
    style F fill:#e1f5ff
```

#### Automated Deployment

```bash
# One-command deployment with validation
./deploy_to_aws.sh
```

This script automatically:
1. ✅ Runs pre-deployment connectivity checks
2. 🏗️ Deploys infrastructure with Terraform
3. 🐳 Builds and pushes Docker image to ECR
4. 🔄 Updates ECS service
5. ✅ Runs post-deployment validation

#### Manual Deployment Steps

**1. Deploy Infrastructure**
```bash
cd seva-arogya-infra
terraform init
terraform apply
```

**2. Build Docker Image**
```bash
docker build -t seva-arogya:latest .
```

**3. Push to ECR**
```bash
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.ap-south-1.amazonaws.com

docker tag seva-arogya:latest \
  <account-id>.dkr.ecr.ap-south-1.amazonaws.com/seva-arogya:latest

docker push \
  <account-id>.dkr.ecr.ap-south-1.amazonaws.com/seva-arogya:latest
```

**4. Update ECS Service**
```bash
aws ecs update-service \
  --cluster seva-arogya-cluster \
  --service seva-arogya-service \
  --force-new-deployment
```

### 🌍 Deployment Environments

| Environment | ECS Tasks | RDS Size | Purpose |
|-------------|-----------|----------|---------|
| 🔧 **Development** | 1 | db.t3.small | Local testing |
| 🧪 **Staging** | 2 | db.t3.medium | Pre-production validation |
| 🚀 **Production** | 2-10 (auto-scale) | db.t3.large (Multi-AZ) | Live system |

---

## 🧪 Testing

### 🔍 AWS Connectivity Tests

```bash
# Comprehensive diagnostic
python test_aws_connectivity.py

# Cognito-specific test
python test_cognito_connection.py

# Pre-deployment validation
bash scripts/pre_deploy_check.sh

# Post-deployment validation
bash scripts/validate_deployment.sh <API_URL>
```

### 🏥 Health Checks

```bash
# Basic health
curl http://your-alb-url/health

# AWS connectivity
curl http://your-alb-url/health/aws-connectivity
```

**Expected Response:**
```json
{
  "status": "healthy",
  "services": {
    "cognito": {"status": "healthy", "latency_ms": 45},
    "s3": {"status": "healthy", "latency_ms": 23},
    "transcribe": {"status": "healthy", "latency_ms": 67},
    "comprehend": {"status": "healthy", "latency_ms": 89},
    "secrets_manager": {"status": "healthy", "latency_ms": 34}
  }
}
```

### 🧪 API Testing Examples

**Test Authentication:**
```bash
# Register
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!","name":"Test User"}'

# Login
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"email":"test@example.com","password":"Test123!"}'
```

**Test Audio Upload:**
```bash
curl -X POST http://localhost:5000/api/v1/audio/upload \
  -b cookies.txt \
  -F "audio=@sample.mp3"
```

**Test Transcription:**
```bash
# Start transcription
curl -X POST http://localhost:5000/api/v1/transcribe \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"s3_key":"audio/test@example.com/sample.mp3"}'

# Check status
curl http://localhost:5000/api/v1/transcribe/status/<job_id> \
  -b cookies.txt

# Get results
curl http://localhost:5000/api/v1/transcribe/result/<job_id> \
  -b cookies.txt
```

---

## 🔧 Troubleshooting

### Common Issues & Solutions

```mermaid
graph TD
    A[Issue?] --> B{Connection Error?}
    B -->|Yes| C[Check AWS Credentials]
    B -->|No| D{Database Error?}
    
    C --> E[Run test_aws_connectivity.py]
    E --> F{Fixed?}
    F -->|No| G[Check VPN/Firewall]
    
    D -->|Yes| H[Check DATABASE_URL]
    H --> I[Verify PostgreSQL Running]
    
    B -->|No| J{Deployment Timeout?}
    J -->|Yes| K[Wait 2-3 min for NAT]
    K --> L[Check Security Groups]
    
    style A fill:#ffebee
    style F fill:#e8f5e9
    style G fill:#fff3e0
```

#### 🚫 "Cannot connect to endpoint URL"

**Symptoms:** AWS service connection failures

**Solutions:**
1. Check internet connection
2. Verify AWS credentials in `.env`
3. Disable VPN temporarily
4. Check firewall settings
5. Run diagnostic: `python test_aws_connectivity.py`

```bash
# Verify credentials
aws sts get-caller-identity

# Test connectivity
python test_aws_connectivity.py
```

#### ⏱️ "Post-deployment validation timeout"

**Symptoms:** Health checks fail after deployment

**Solutions:**
1. Wait 2-3 minutes for NAT gateway initialization
2. Check security groups allow outbound HTTPS (443)
3. Verify ECS tasks are running
4. Check CloudWatch logs

```bash
# Check ECS tasks
aws ecs list-tasks --cluster seva-arogya-cluster

# View logs
aws logs tail "/ecs/seva-arogya-dev" --follow
```

#### 🗄️ "Database connection fails"

**Symptoms:** Health check shows database unhealthy

**Solutions:**
1. Verify RDS endpoint in Secrets Manager
2. Check security group rules (port 5432)
3. Ensure database exists
4. Test connection locally

```bash
# Test database connection
psql -h <rds-endpoint> -U postgres -d seva_arogya

# Check if database exists
psql -U postgres -l | grep seva_arogya
```

#### 🔐 "Authentication failures"

**Symptoms:** Login fails or JWT errors

**Solutions:**
1. Verify Cognito User Pool ID and Client ID
2. Check user is confirmed in Cognito
3. Ensure password meets requirements
4. Clear browser cookies/cache

```bash
# List Cognito users
aws cognito-idp list-users \
  --user-pool-id <pool-id>

# Confirm user manually
aws cognito-idp admin-confirm-sign-up \
  --user-pool-id <pool-id> \
  --username <email>
```

### 🐛 Debug Mode

```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG
export FLASK_DEBUG=True
python app.py

# Check application logs
tail -f logs/app.log

# Check ECS logs (production)
aws logs tail "/ecs/seva-arogya-dev" --follow --region ap-south-1

# Filter for errors
aws logs filter-log-events \
  --log-group-name /ecs/seva-arogya-dev \
  --filter-pattern "ERROR" \
  --region ap-south-1
```

### 📊 Monitoring Dashboard

```bash
# Get CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=seva-arogya-service \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 3600 \
  --statistics Average
```

---

## 📁 Project Structure

```
seva-arogya/
├── 🐍 app.py                      # Main Flask application
├── 📦 requirements.txt            # Python dependencies
├── 🐳 Dockerfile                  # Container definition
├── 🚀 deploy_to_aws.sh           # Deployment automation
│
├── 🔧 aws_services/              # AWS service managers
│   ├── auth_manager.py           # Cognito authentication
│   ├── transcribe_manager.py     # Speech-to-text
│   ├── transcribe_streaming_manager.py  # Real-time transcription
│   ├── comprehend_manager.py     # Medical NLP
│   ├── storage_manager.py        # S3 operations
│   ├── database_manager.py       # Database operations
│   ├── session_manager.py        # Session handling
│   └── connectivity_checker.py   # Health checks
│
├── 📊 models/                    # Database models
│   ├── prescription.py           # Prescription model
│   └── transcription.py          # Transcription model
│
├── 🎨 templates/                 # HTML templates
│   ├── login.html
│   ├── home.html
│   ├── transcription.html
│   └── final_prescription.html
│
├── 📜 scripts/                   # Deployment scripts
│   ├── pre_deploy_check.sh      # Pre-deployment validation
│   └── validate_deployment.sh   # Post-deployment validation
│
├── 🗄️ migrations/                # Database migrations
│   ├── 001_add_streaming_columns.sql
│   ├── migration_manager.py
│   └── run_migration.py
│
├── 🧪 tests/                     # Test files
│   ├── test_aws_connectivity.py
│   └── test_cognito_connection.py
│
└── 🏗️ seva-arogya-infra/        # Terraform infrastructure
    ├── main.tf
    ├── modules/
    │   ├── alb/
    │   ├── ecs/
    │   ├── rds/
    │   ├── s3/
    │   ├── cognito/
    │   └── iam/
    └── ...
```

### Key Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| 🐍 **app.py** | Main application entry | Flask 3.0 |
| 🔧 **aws_services/** | AWS integration layer | Boto3 |
| 📊 **models/** | Data models | SQLAlchemy |
| 🎨 **templates/** | UI templates | Jinja2 + Tailwind |
| 🏗️ **seva-arogya-infra/** | Infrastructure as Code | Terraform |

---

## 🔒 Security

```mermaid
graph TB
    subgraph "Security Layers"
        A[🌐 Network Security]
        B[🔐 Authentication]
        C[🔑 Authorization]
        D[🛡️ Data Protection]
        E[📝 Audit Logging]
    end
    
    A --> A1[VPC with Private Subnets]
    A --> A2[Security Groups]
    A --> A3[HTTPS/TLS 1.2+]
    
    B --> B1[AWS Cognito]
    B --> B2[JWT Tokens]
    B --> B3[MFA Support]
    
    C --> C1[Role-Based Access]
    C --> C2[Row-Level Security]
    C --> C3[IAM Policies]
    
    D --> D1[AES-256 Encryption at Rest]
    D --> D2[TLS Encryption in Transit]
    D --> D3[Secrets Manager]
    
    E --> E1[CloudWatch Logs]
    E --> E2[Audit Trail]
    E --> E3[7-Year Retention]
    
    style A fill:#ffebee
    style B fill:#e3f2fd
    style C fill:#f3e5f5
    style D fill:#e8f5e9
    style E fill:#fff3e0
```

### Security Features

| Layer | Implementation | Standard |
|-------|----------------|----------|
| 🔐 **Authentication** | AWS Cognito with JWT | OAuth 2.0 |
| 🔑 **Authorization** | Role-based access control | RBAC |
| 🛡️ **Data at Rest** | AES-256 encryption | FIPS 140-2 |
| 🔒 **Data in Transit** | TLS 1.2+ | SSL/TLS |
| 🗝️ **Secrets** | AWS Secrets Manager | Encrypted |
| 📝 **Audit Logs** | CloudWatch + Database | 7-year retention |
| 🌐 **Network** | VPC + Security Groups | Least privilege |

### Compliance

- ✅ HTTPS-only communication
- ✅ Encrypted database backups
- ✅ Audit trail for all actions
- ✅ Data residency in India (ap-south-1)
- ✅ DISHA-ready architecture
- ✅ HIPAA-aligned practices

---

## ⚡ Performance

```mermaid
graph LR
    A[Request] --> B[CloudFront CDN]
    B --> C[ALB]
    C --> D[ECS Auto-Scaling<br/>2-10 tasks]
    D --> E[Connection Pool<br/>2-10 connections]
    E --> F[RDS Multi-AZ]
    
    style B fill:#e3f2fd
    style D fill:#e8f5e9
    style E fill:#fff3e0
    style F fill:#f3e5f5
```

### Performance Targets

| Metric | Target | Implementation |
|--------|--------|----------------|
| 🚀 **API Response** | < 500ms | Connection pooling, caching |
| 🎤 **Transcription** | < 2s | AWS Transcribe Medical |
| 📄 **PDF Generation** | < 1s | Optimized templates |
| 🌐 **Page Load** | < 1.5s | CloudFront CDN |
| 👥 **Concurrent Users** | 500+ | Auto-scaling (2-10 tasks) |
| 📊 **Lighthouse Score** | > 90 | Code splitting, optimization |

### Optimization Features

- ⚡ Connection pooling (2-10 connections)
- 🔄 Retry logic with exponential backoff
- 🌐 CloudFront CDN for static assets
- 🏗️ Multi-AZ deployment for high availability
- 📈 Auto-scaling based on CPU/memory (70% threshold)
- 🗄️ Database indexes on frequently queried fields
- 🔍 Query optimization with SQLAlchemy

---

## 📊 Monitoring

```mermaid
graph TB
    subgraph "Monitoring Stack"
        A[📊 CloudWatch Metrics]
        B[📝 CloudWatch Logs]
        C[🔍 X-Ray Tracing]
        D[🚨 CloudWatch Alarms]
    end
    
    A --> A1[Request Count]
    A --> A2[Latency p50/p95/p99]
    A --> A3[Error Rates]
    A --> A4[CPU/Memory]
    
    B --> B1[Application Logs<br/>30 days]
    B --> B2[Audit Logs<br/>7 years]
    B --> B3[Access Logs<br/>90 days]
    
    C --> C1[Distributed Tracing]
    C --> C2[Service Map]
    C --> C3[Performance Analysis]
    
    D --> D1[CPU > 80%]
    D --> D2[Error Rate > 5%]
    D --> D3[Health Check Failures]
    
    style A fill:#e3f2fd
    style B fill:#fff3e0
    style C fill:#f3e5f5
    style D fill:#ffebee
```

### Monitoring Features

| Component | Metrics | Retention |
|-----------|---------|-----------|
| 📊 **Application** | Requests, latency, errors | 30 days |
| 🔐 **Security** | Login attempts, API calls | 7 years |
| 🏥 **Health** | Service status, connectivity | Real-time |
| 💻 **Infrastructure** | CPU, memory, disk, network | 15 months |

### CloudWatch Alarms

- 🚨 CPU utilization > 80% for 5 minutes
- 🚨 Error rate > 5% for 2 minutes
- 🚨 Health check failures (3 consecutive)
- 🚨 Database connection pool exhaustion
- 🚨 S3 upload failures

### Health Endpoints

```bash
# Basic health check
curl http://your-alb-url/health

# Detailed AWS connectivity
curl http://your-alb-url/health/aws-connectivity
```

---

## 📚 Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| 📖 **README.md** | Quick start & deployment | Developers, DevOps |
| 🏗️ **design.md** | System architecture & design | Architects, Developers |
| 📋 **requirements.md** | Requirements & specifications | Product, Stakeholders |
| 🔧 **.kiro/specs/** | Feature specifications | Development team |
| 🧪 **tests/** | Test documentation | QA, Developers |

---

## 🛠️ Technology Stack

```mermaid
graph TB
    subgraph "Frontend"
        A[React 18+]
        B[TypeScript]
        C[Tailwind CSS]
    end
    
    subgraph "Backend"
        D[Python 3.11+]
        E[Flask 3.0]
        F[SQLAlchemy]
    end
    
    subgraph "Database"
        G[PostgreSQL 15]
        H[Redis Cache]
    end
    
    subgraph "Infrastructure"
        I[Docker]
        J[ECS Fargate]
        K[Terraform]
    end
    
    subgraph "AI/ML"
        L[Transcribe Medical]
        M[Comprehend Medical]
        N[Translate]
    end
    
    A --> D
    D --> G
    I --> J
    K --> J
    D --> L
    D --> M
    D --> N
    
    style A fill:#61dafb
    style D fill:#3776ab
    style G fill:#336791
    style I fill:#2496ed
    style L fill:#ff9900
```

### Stack Details

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| 🎨 **Frontend** | React | 18+ | UI framework |
| 🐍 **Backend** | Python/Flask | 3.11+/3.0 | API server |
| 🗄️ **Database** | PostgreSQL | 15+ | Data persistence |
| 🐳 **Container** | Docker | Latest | Containerization |
| ☁️ **Orchestration** | ECS Fargate | - | Container hosting |
| 🏗️ **IaC** | Terraform | 1.0+ | Infrastructure |
| 🎤 **STT** | Transcribe Medical | - | Speech-to-text |
| 🧠 **NLP** | Comprehend Medical | - | Entity extraction |
| 🌐 **Translation** | AWS Translate | - | Multi-language |

---

## 🤝 Support

### Getting Help

1. 📖 Check documentation (README.md, design.md)
2. 🔍 Run diagnostic scripts (`test_aws_connectivity.py`)
3. 📝 Review CloudWatch logs
4. 🌐 Check AWS service status
5. 🐛 Open an issue with detailed logs

### Useful Commands

```bash
# Check system health
curl http://localhost:5000/health

# Run diagnostics
python test_aws_connectivity.py

# View logs
tail -f logs/app.log

# Check AWS credentials
aws sts get-caller-identity

# Test database connection
psql -h localhost -U postgres -d seva_arogya
```

---

## 📄 License

**Proprietary** - SEVA Arogya

---

## 📌 Version Information

| Info | Value |
|------|-------|
| **Version** | 2.0 |
| **Last Updated** | 2026-03-01 |
| **Status** | ✅ Production Ready |
| **Python** | 3.9+ |
| **AWS Region** | ap-south-1 (Mumbai) |

---

## 🚀 Quick Links

- 📖 [System Design](design.md)
- 📋 [Requirements](requirements.md)
- 🔧 [Feature Specs](.kiro/specs/)
- 🧪 [Testing Guide](TESTING_GUIDE.md)
- ☁️ [AWS Setup](QUICKSTART_AWS.md)

---

<div align="center">

**Built with ❤️ for Indian Healthcare**

🏥 Transforming Clinical Documentation | 🎤 Voice-First Design | ☁️ Cloud-Native Architecture

</div>
