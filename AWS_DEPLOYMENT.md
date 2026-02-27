# AWS Services Deployment Guide

This document provides instructions for deploying the SEVA Arogya Flask application with AWS services integration.

## Prerequisites

- AWS Account with appropriate permissions
- Terraform infrastructure deployed (see `seva-arogya-infra/`)
- Python 3.8+ installed
- AWS CLI configured with credentials

## AWS Services Required

The application integrates with the following AWS services:

1. **AWS Cognito** - User authentication and authorization
2. **AWS Transcribe Medical** - Medical audio transcription
3. **AWS Comprehend Medical** - Medical entity extraction
4. **AWS Secrets Manager** - Secure configuration storage
5. **AWS S3** - File storage (audio and PDFs)
6. **AWS RDS PostgreSQL** - Database

## IAM Permissions

### ECS Task Role Permissions

The ECS task role must have the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cognito-idp:InitiateAuth",
        "cognito-idp:SignUp",
        "cognito-idp:ConfirmSignUp",
        "cognito-idp:GetUser",
        "cognito-idp:GlobalSignOut"
      ],
      "Resource": "arn:aws:cognito-idp:REGION:ACCOUNT_ID:userpool/USER_POOL_ID"
    },
    {
      "Effect": "Allow",
      "Action": [
        "transcribe:StartMedicalTranscriptionJob",
        "transcribe:GetMedicalTranscriptionJob"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "comprehendmedical:DetectEntitiesV2"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::AUDIO_BUCKET_NAME/*",
        "arn:aws:s3:::PDF_BUCKET_NAME/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:seva-arogya/*"
      ]
    }
  ]
}
```

### Local Development Permissions

For local development, your AWS user/role needs the same permissions as the ECS task role.

## AWS Secrets Manager Configuration

### Database Credentials Secret

Create a secret named `seva-arogya/db-credentials` with the following JSON structure:

```json
{
  "host": "your-rds-endpoint.region.rds.amazonaws.com",
  "port": 5432,
  "database": "seva_arogya",
  "username": "postgres",
  "password": "your-secure-password"
}
```

### Flask Secret Key

Create a secret named `seva-arogya/flask-secret` with a random string:

```json
{
  "secret_key": "your-random-secret-key-here"
}
```

Or as a plain string:
```
your-random-secret-key-here
```

### JWT Secret

Create a secret named `seva-arogya/jwt-secret` with a random string:

```json
{
  "jwt_secret": "your-jwt-secret-here"
}
```

## Environment Variables

### Required Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# AWS Configuration
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your-access-key  # Only for local development
AWS_SECRET_ACCESS_KEY=your-secret-key  # Only for local development

# AWS Cognito
AWS_COGNITO_USER_POOL_ID=ap-south-1_xxxxxxxxx
AWS_COGNITO_CLIENT_ID=your-client-id
AWS_COGNITO_CLIENT_SECRET=your-client-secret  # Optional

# AWS S3 Buckets
S3_AUDIO_BUCKET=seva-arogya-audio
S3_PDF_BUCKET=seva-arogya-prescriptions

# AWS Secrets Manager
DB_SECRET_NAME=seva-arogya/db-credentials
FLASK_SECRET_NAME=seva-arogya/flask-secret
JWT_SECRET_NAME=seva-arogya/jwt-secret

# Database Configuration (fallback if Secrets Manager unavailable)
DATABASE_URL=postgresql://user:password@localhost:5432/seva_arogya

# CORS Configuration
CORS_ALLOWED_ORIGINS=http://localhost:5000,http://localhost:3000

# Logging Configuration
LOG_LEVEL=INFO
```

### ECS Environment Variables

For ECS deployment, configure the following environment variables in your task definition:

- `AWS_REGION`
- `AWS_COGNITO_USER_POOL_ID`
- `AWS_COGNITO_CLIENT_ID`
- `AWS_COGNITO_CLIENT_SECRET` (if using)
- `S3_AUDIO_BUCKET`
- `S3_PDF_BUCKET`
- `DB_SECRET_NAME`
- `FLASK_SECRET_NAME`
- `JWT_SECRET_NAME`
- `CORS_ALLOWED_ORIGINS`
- `LOG_LEVEL`
- `FLASK_ENV=production`

**Note:** Do NOT set `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` in ECS. The task role provides credentials automatically.

## Database Setup

### Create Database Tables

The application automatically creates required tables on startup. To manually create tables:

```python
from aws_services.database_manager import DatabaseManager
from models.prescription import Prescription
from models.transcription import Transcription

# Initialize database manager
db_manager = DatabaseManager(db_config)

# Create tables
db_manager.execute_with_retry(Prescription.create_table_sql())
db_manager.execute_with_retry(Transcription.create_table_sql())
```

## Local Development Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure AWS credentials:**
   ```bash
   aws configure
   ```

3. **Create `.env` file:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Access the application:**
   - Open browser to `http://localhost:5000`

## Production Deployment (ECS)

### 1. Build Docker Image

```bash
docker build -t seva-arogya:latest .
```

### 2. Push to ECR

```bash
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com
docker tag seva-arogya:latest ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/seva-arogya:latest
docker push ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/seva-arogya:latest
```

### 3. Update ECS Task Definition

Update your ECS task definition with:
- Container image URI
- Environment variables
- Task role ARN with required permissions
- Execution role ARN

### 4. Deploy to ECS

```bash
aws ecs update-service --cluster seva-arogya-cluster --service seva-arogya-service --force-new-deployment
```

## Health Check

The application provides a health check endpoint at `/health`:

```bash
curl http://localhost:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": 1234567890.123,
  "checks": {
    "database": "healthy",
    "secrets_manager": "healthy"
  }
}
```

## Monitoring and Logging

### CloudWatch Logs

The application uses structured JSON logging for CloudWatch integration. Logs include:

- Request IDs from AWS services
- Operation duration
- Error codes and messages
- Service names and operations

### Log Groups

Configure CloudWatch log groups in your ECS task definition:

```json
{
  "logConfiguration": {
    "logDriver": "awslogs",
    "options": {
      "awslogs-group": "/ecs/seva-arogya",
      "awslogs-region": "ap-south-1",
      "awslogs-stream-prefix": "ecs"
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Authentication Fails**
   - Verify Cognito User Pool ID and Client ID
   - Check IAM permissions for cognito-idp actions
   - Ensure user is confirmed in Cognito

2. **Transcription Fails**
   - Verify S3 bucket permissions
   - Check audio file format (must be wav, mp3, flac, or mp4)
   - Ensure file size is under 16MB
   - Verify IAM permissions for transcribe actions

3. **Database Connection Fails**
   - Verify RDS endpoint and credentials in Secrets Manager
   - Check security group rules allow connections
   - Ensure database exists and tables are created

4. **Secrets Manager Access Denied**
   - Verify IAM permissions for secretsmanager:GetSecretValue
   - Check secret names match configuration
   - Ensure secrets exist in the correct region

### Debug Mode

For local development, enable debug logging:

```bash
export LOG_LEVEL=DEBUG
export FLASK_DEBUG=True
python app.py
```

## Security Best Practices

1. **Never commit credentials** - Use Secrets Manager or environment variables
2. **Use HTTPS in production** - Configure ALB with SSL certificate
3. **Rotate secrets regularly** - Use AWS Secrets Manager rotation
4. **Limit IAM permissions** - Follow principle of least privilege
5. **Enable CloudTrail** - Monitor API calls and access
6. **Use VPC endpoints** - For private communication with AWS services
7. **Enable encryption** - S3 server-side encryption, RDS encryption at rest

## Cost Optimization

1. **S3 Lifecycle Policies** - Archive old audio files to Glacier
2. **RDS Instance Sizing** - Right-size based on usage
3. **Cognito Pricing** - Monitor MAU (Monthly Active Users)
4. **Transcribe Medical** - Batch process when possible
5. **CloudWatch Logs Retention** - Set appropriate retention periods

## Support

For issues or questions:
- Check CloudWatch logs for error details
- Review IAM permissions
- Verify AWS service quotas
- Contact AWS Support for service-specific issues
