---
inclusion: auto
---

# Technology Stack & Build System

## Core Technologies

### Backend
- **Framework**: Flask (Python 3.11+)
- **WSGI Server**: Gunicorn with eventlet worker for WebSocket support
- **Real-time**: Flask-SocketIO with eventlet async mode
- **Database**: PostgreSQL 13+ (AWS RDS)
- **ORM**: Direct SQL with psycopg2-binary

### Frontend
- **Framework**: Vanilla JavaScript (no build system)
- **Styling**: Tailwind CSS (CDN)
- **Icons**: Material Symbols
- **Templates**: Jinja2 server-side rendering

### AWS Services
- **Authentication**: AWS Cognito (JWT tokens)
- **Speech-to-Text**: AWS Transcribe Medical
- **NLP**: AWS Comprehend Medical
- **Translation**: AWS Translate
- **Storage**: AWS S3 (audio files, PDF prescriptions)
- **Secrets**: AWS Secrets Manager
- **Container**: ECS Fargate (Docker)
- **Load Balancer**: Application Load Balancer
- **Monitoring**: CloudWatch + X-Ray

### Infrastructure
- **IaC**: Terraform (modules in `seva-arogya-infra/`)
- **Container**: Docker with Python 3.11-slim base
- **Deployment**: ECS Fargate with blue-green deployment

## Key Dependencies

```
Flask==3.0.0
flask-socketio==5.3.4
eventlet==0.33.3
boto3==1.34.0
psycopg2-binary==2.9.9
gunicorn==21.2.0
python-dotenv==1.0.0
amazon-transcribe==0.6.2
pydub==0.25.1
hypothesis==6.92.0
pytest==7.4.3
```

## Common Commands

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py
# Runs on http://localhost:5000 with debug mode

# Run with Gunicorn (production-like)
gunicorn -k eventlet -w 1 -b 0.0.0.0:5000 app:app
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_transcription_page_bug_exploration.py

# Run property-based tests (Hypothesis)
pytest tests/test_transcription_page_preservation.py
```

### Docker

```bash
# Build image
docker build -t seva-arogya-backend .

# Run container locally
docker run -p 5000:5000 --env-file .env seva-arogya-backend

# Push to ECR (after AWS authentication)
docker tag seva-arogya-backend:latest <ecr-url>:latest
docker push <ecr-url>:latest
```

### Infrastructure (Terraform)

```bash
cd seva-arogya-infra

# Initialize
terraform init

# Plan changes
terraform plan -out=tfplan

# Apply infrastructure
terraform apply tfplan

# Get outputs
terraform output api_base_url

# Destroy (WARNING: deletes all resources)
terraform destroy
```

### AWS Deployment

```bash
# Full deployment with validation
./deploy_to_aws.sh

# Force ECS service update
aws ecs update-service \
  --cluster seva-arogya-dev-cluster \
  --service seva-arogya-dev-api \
  --force-new-deployment \
  --region ap-south-1

# View logs
aws logs tail "/ecs/seva-arogya-dev" --follow --region ap-south-1
```

### Health Checks

```bash
# Basic health check
curl http://localhost:5000/health

# AWS connectivity check
curl http://localhost:5000/health/aws-connectivity

# Deployment validation
cd seva-arogya-infra
bash scripts/validate_deployment.sh $(terraform output -raw api_base_url)
```

## Environment Configuration

Configuration is managed via `.env` file (see `.env.example` for template):

```bash
# AWS Configuration
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>

# Database (loaded from Secrets Manager in production)
DB_HOST=localhost
DB_NAME=sevaarogya
DB_USERNAME=sevaadmin
DB_PASSWORD=<password>

# Application
FLASK_ENV=development
SECRET_KEY=<random-string>
LOG_LEVEL=INFO

# AWS Service Configuration
COGNITO_USER_POOL_ID=<pool-id>
COGNITO_CLIENT_ID=<client-id>
S3_AUDIO_BUCKET=<bucket-name>
S3_PDF_BUCKET=<bucket-name>
```

## Architecture Notes

- **Async Mode**: Uses eventlet for WebSocket support (Flask-SocketIO)
- **Database Pooling**: Connection pooling managed by psycopg2
- **Secrets**: Production uses AWS Secrets Manager; local uses .env
- **Logging**: Structured JSON logging in production, text in development
- **Error Handling**: Centralized error handlers in `utils/error_handler.py`
- **Migrations**: SQL migrations in `migrations/` with MigrationManager
