# SEVA Arogya - Voice-Enabled Clinical Prescription System

Voice-enabled clinical note capture and prescription generation system built on AWS infrastructure.

## Quick Start

### Prerequisites
- Python 3.9+
- AWS Account with configured credentials
- PostgreSQL (local) or AWS RDS

### Installation

```bash
# Clone and setup
git clone <repository-url>
cd seva-arogya

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your AWS credentials and configuration

# Run the application
python app.py
```

Access at: http://localhost:5000

### Default Login Credentials (Demo Mode)
- Email: `doctor@hospital.com` | Password: `password123`
- Email: `admin@seva.com` | Password: `admin123`

## Architecture

SEVA Arogya follows a 5-layer cloud-native architecture:

1. **Presentation**: React 18+ SPA with TypeScript
2. **API Gateway**: AWS Application Load Balancer
3. **Application**: Flask on ECS Fargate
4. **Data**: PostgreSQL (RDS) + S3
5. **Integration**: AWS SDK (Boto3)

### AWS Services
- **Cognito**: Authentication & authorization
- **Transcribe Medical**: Medical audio transcription
- **Comprehend Medical**: Medical entity extraction
- **S3**: File storage (audio & PDFs)
- **RDS PostgreSQL**: Database
- **Secrets Manager**: Configuration management

## Features

### Implemented
- ✅ User authentication (AWS Cognito)
- ✅ Voice capture and transcription
- ✅ Medical entity extraction
- ✅ Prescription generation
- ✅ PDF storage and retrieval
- ✅ Live audio streaming transcription
- ✅ Multi-language support

### UI Pages
1. **Login** (`/login`) - Email/password authentication
2. **Home** (`/home`) - Patient search and consultation start
3. **Transcription** (`/transcription`) - Voice capture with live transcription
4. **Final Prescription** (`/final-prescription`) - Review and finalize

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/verify` - Email verification
- `POST /api/v1/auth/logout` - User logout

### Audio & Transcription
- `POST /api/v1/audio/upload` - Upload audio file
- `POST /api/v1/transcribe` - Start transcription
- `GET /api/v1/transcribe/status/<job_id>` - Check status
- `GET /api/v1/transcribe/result/<job_id>` - Get results

### Prescriptions
- `POST /api/v1/prescriptions` - Create prescription
- `GET /api/v1/prescriptions/<id>/download` - Download PDF

### Health
- `GET /health` - Basic health check
- `GET /health/aws-connectivity` - AWS services connectivity

## Configuration

### Required Environment Variables

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
```

See `.env.example` for complete configuration.

## Deployment

### Local Development

```bash
# Run application
python app.py

# Run tests
python test_aws_connectivity.py
```

### AWS Deployment

```bash
# Deploy with validation
./deploy_to_aws.sh
```

This will:
1. Run pre-deployment connectivity checks
2. Deploy infrastructure with Terraform
3. Build and push Docker image to ECR
4. Update ECS service
5. Run post-deployment validation

### Manual Deployment Steps

1. **Deploy Infrastructure**
   ```bash
   cd seva-arogya-infra
   terraform init
   terraform apply
   ```

2. **Build Docker Image**
   ```bash
   docker build -t seva-arogya:latest .
   ```

3. **Push to ECR**
   ```bash
   aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.ap-south-1.amazonaws.com
   docker tag seva-arogya:latest <account-id>.dkr.ecr.ap-south-1.amazonaws.com/seva-arogya:latest
   docker push <account-id>.dkr.ecr.ap-south-1.amazonaws.com/seva-arogya:latest
   ```

4. **Update ECS Service**
   ```bash
   aws ecs update-service --cluster seva-arogya-cluster --service seva-arogya-service --force-new-deployment
   ```

## Testing

### AWS Connectivity Tests

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

### Health Checks

```bash
# Basic health
curl http://your-alb-url/health

# AWS connectivity
curl http://your-alb-url/health/aws-connectivity
```

## Troubleshooting

### Common Issues

**"Cannot connect to endpoint URL"**
- Check internet connection
- Verify AWS credentials in `.env`
- Disable VPN temporarily
- Check firewall settings
- Run: `python test_aws_connectivity.py`

**"Post-deployment validation timeout"**
- Wait 2-3 minutes for NAT gateway and routes
- Check security groups allow outbound HTTPS
- Verify ECS tasks are running
- Check CloudWatch logs

**Database connection fails**
- Verify RDS endpoint in Secrets Manager
- Check security group rules
- Ensure database exists

### Debug Mode

```bash
export LOG_LEVEL=DEBUG
export FLASK_DEBUG=True
python app.py
```

### Check Logs

```bash
# ECS logs
aws logs tail "/ecs/seva-arogya-dev" --follow --region ap-south-1

# Filter for errors
aws logs filter-log-events \
  --log-group-name /ecs/seva-arogya-dev \
  --filter-pattern "ERROR" \
  --region ap-south-1
```

## Project Structure

```
seva-arogya/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container definition
├── deploy_to_aws.sh           # Deployment script
├── aws_services/              # AWS service managers
│   ├── auth_manager.py
│   ├── transcribe_manager.py
│   ├── comprehend_manager.py
│   ├── storage_manager.py
│   ├── database_manager.py
│   └── connectivity_checker.py
├── models/                    # Database models
│   ├── prescription.py
│   └── transcription.py
├── templates/                 # HTML templates
│   ├── login.html
│   ├── home.html
│   ├── transcription.html
│   └── final_prescription.html
├── static/                    # Static assets
├── scripts/                   # Deployment scripts
│   ├── pre_deploy_check.sh
│   └── validate_deployment.sh
├── migrations/                # Database migrations
├── tests/                     # Test files
└── seva-arogya-infra/        # Terraform infrastructure
```

## Security

- AWS Cognito authentication with JWT tokens
- Secrets Manager for sensitive data
- S3 server-side encryption (AES-256)
- HTTPS/TLS for all connections
- VPC with private subnets
- Security groups with least privilege
- Audit logging enabled

## Performance

- Connection pooling (2-10 connections)
- Retry logic with exponential backoff
- CloudFront CDN for static assets
- Multi-AZ deployment
- Auto-scaling (2-10 ECS tasks)
- Database indexes optimized

## Monitoring

- CloudWatch logs and metrics
- Health check endpoints
- X-Ray distributed tracing
- CloudWatch alarms for errors and latency
- Audit logs for security events

## Documentation

- `design.md` - System design and architecture
- `.kiro/specs/` - Feature specifications
- `tests/` - Test documentation

## Support

For issues or questions:
1. Check CloudWatch logs
2. Run diagnostic scripts
3. Review documentation
4. Check AWS service status

## License

Proprietary - SEVA Arogya

## Version

**Version**: 2.0  
**Last Updated**: 2026-03-01  
**Status**: Production Ready
