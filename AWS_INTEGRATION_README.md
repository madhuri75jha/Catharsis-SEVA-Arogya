# AWS Services Integration - SEVA Arogya

This document describes the AWS services integration implemented in the SEVA Arogya Flask application.

## Overview

The application integrates with multiple AWS services to provide secure authentication, medical audio transcription, entity extraction, and file storage capabilities.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Flask Application                        │
├─────────────────────────────────────────────────────────────┤
│  Routes Layer                                                │
│  - Authentication (/api/v1/auth/*)                          │
│  - Audio Upload (/api/v1/audio/upload)                      │
│  - Transcription (/api/v1/transcribe/*)                     │
│  - Prescriptions (/api/v1/prescriptions/*)                  │
│  - Health Check (/health)                                    │
├─────────────────────────────────────────────────────────────┤
│  Service Managers Layer                                      │
│  - ConfigManager    - AuthManager                           │
│  - StorageManager   - TranscribeManager                     │
│  - ComprehendManager - DatabaseManager                      │
├─────────────────────────────────────────────────────────────┤
│  AWS Services Layer                                          │
│  - Cognito          - Transcribe Medical                    │
│  - Comprehend Medical - S3                                   │
│  - Secrets Manager  - RDS PostgreSQL                        │
└─────────────────────────────────────────────────────────────┘
```

## Implemented Features

### 1. Configuration Management (`aws_services/config_manager.py`)

**Features:**
- Loads configuration from environment variables
- Retrieves secrets from AWS Secrets Manager with caching
- Fallback to environment variables if Secrets Manager unavailable
- Validates required configuration at startup

**Usage:**
```python
from aws_services.config_manager import ConfigManager

config = ConfigManager()
db_credentials = config.get_database_credentials()
flask_secret = config.get_flask_secret_key()
```

### 2. Authentication (`aws_services/auth_manager.py`)

**Features:**
- User authentication with AWS Cognito
- User registration with email verification
- Token refresh and validation
- Secure session management
- User logout with token revocation

**API Endpoints:**
- `POST /api/v1/auth/login` - Authenticate user
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/verify` - Verify email with code
- `POST /api/v1/auth/logout` - Logout user

**Example:**
```bash
# Login
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Register
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123", "name": "John Doe"}'

# Verify
curl -X POST http://localhost:5000/api/v1/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "code": "123456"}'
```

### 3. Storage Management (`aws_services/storage_manager.py`)

**Features:**
- Audio file upload to S3 with validation
- PDF file upload with encryption (AES256)
- Presigned URL generation for downloads
- File format validation (wav, mp3, flac, mp4)
- File size limit enforcement (16MB)

**API Endpoints:**
- `POST /api/v1/audio/upload` - Upload audio file
- `GET /api/v1/prescriptions/<id>/download` - Get download URL

**Example:**
```bash
# Upload audio
curl -X POST http://localhost:5000/api/v1/audio/upload \
  -H "Cookie: session=..." \
  -F "audio=@recording.mp3"
```

### 4. Medical Transcription (`aws_services/transcribe_manager.py`)

**Features:**
- Start medical transcription jobs
- Poll transcription job status
- Retrieve completed transcripts
- Medical specialty vocabulary support
- Error handling with descriptive messages

**API Endpoints:**
- `POST /api/v1/transcribe` - Start transcription
- `GET /api/v1/transcribe/status/<job_id>` - Check status
- `GET /api/v1/transcribe/result/<job_id>` - Get transcript

**Example:**
```bash
# Start transcription
curl -X POST http://localhost:5000/api/v1/transcribe \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"s3_key": "audio/user123/20240227_120000_recording.mp3"}'

# Check status
curl http://localhost:5000/api/v1/transcribe/status/job-id-here \
  -H "Cookie: session=..."

# Get result
curl http://localhost:5000/api/v1/transcribe/result/job-id-here \
  -H "Cookie: session=..."
```

### 5. Medical Entity Extraction (`aws_services/comprehend_manager.py`)

**Features:**
- Extract medical entities from text
- Identify medications, conditions, dosages, procedures, anatomy
- Confidence score filtering (>= 0.5)
- Entity categorization
- Attribute extraction (dosage, frequency, etc.)

**Entity Types:**
- Medications
- Medical conditions
- Procedures
- Anatomy
- Test/Treatment/Procedure
- Attributes (dosage, frequency, duration, etc.)

**Example Response:**
```json
{
  "success": true,
  "transcript": "Patient has hypertension. Prescribed lisinopril 10mg once daily.",
  "entities": [
    {
      "text": "hypertension",
      "category": "MEDICAL_CONDITION",
      "type": "DX_NAME",
      "confidence": 0.98
    },
    {
      "text": "lisinopril",
      "category": "MEDICATION",
      "type": "GENERIC_NAME",
      "confidence": 0.99,
      "attributes": [
        {
          "type": "DOSAGE",
          "text": "10mg",
          "confidence": 0.97
        },
        {
          "type": "FREQUENCY",
          "text": "once daily",
          "confidence": 0.95
        }
      ]
    }
  ]
}
```

### 6. Database Management (`aws_services/database_manager.py`)

**Features:**
- PostgreSQL connection pooling (2-10 connections)
- Retry logic with exponential backoff
- Health check endpoint
- Graceful connection cleanup
- Transaction support

**Models:**
- `Prescription` - Stores prescription data with S3 PDF reference
- `Transcription` - Stores transcription jobs and results

### 7. Error Handling (`utils/error_handler.py`)

**Features:**
- Consistent AWS error handling
- User-friendly error messages
- Exponential backoff retry decorator
- HTTP status code mapping
- Request ID logging

**Error Types:**
- `AuthenticationError` - Authentication failures
- `ValidationError` - Input validation errors
- `ResourceNotFoundError` - Resource not found
- `ServiceUnavailableError` - Service unavailable

### 8. Logging (`utils/logger.py`)

**Features:**
- Structured JSON logging for CloudWatch
- Request ID context management
- Log level configuration
- Operation duration tracking
- Service and operation tagging

**Log Format:**
```json
{
  "timestamp": "2024-02-27T12:00:00.000Z",
  "level": "INFO",
  "logger": "app",
  "message": "User authenticated successfully",
  "service": "cognito-idp",
  "operation": "authenticate",
  "duration_ms": 245.3,
  "request_id": "abc-123-def"
}
```

## API Reference

### Authentication Endpoints

#### POST /api/v1/auth/login
Authenticate user with Cognito.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful"
}
```

#### POST /api/v1/auth/register
Register new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "John Doe"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Registration successful. Please check your email for verification code.",
  "user_confirmed": false
}
```

#### POST /api/v1/auth/verify
Verify user email.

**Request:**
```json
{
  "email": "user@example.com",
  "code": "123456"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Account verified successfully. You can now login."
}
```

### Audio & Transcription Endpoints

#### POST /api/v1/audio/upload
Upload audio file to S3.

**Request:** Multipart form data with `audio` field

**Response:**
```json
{
  "success": true,
  "message": "Audio uploaded successfully",
  "s3_key": "audio/user123/20240227_120000_recording.mp3"
}
```

#### POST /api/v1/transcribe
Start transcription job.

**Request:**
```json
{
  "s3_key": "audio/user123/20240227_120000_recording.mp3"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Transcription started",
  "job_id": "medical-transcription-abc-123"
}
```

#### GET /api/v1/transcribe/status/<job_id>
Check transcription status.

**Response:**
```json
{
  "success": true,
  "status": "COMPLETED",
  "job_id": "medical-transcription-abc-123"
}
```

#### GET /api/v1/transcribe/result/<job_id>
Get transcription result with entities.

**Response:**
```json
{
  "success": true,
  "transcript": "Patient has hypertension...",
  "entities": [...],
  "categorized_entities": {
    "medications": [...],
    "conditions": [...],
    "procedures": [...]
  }
}
```

### Prescription Endpoints

#### POST /api/v1/prescriptions
Create prescription with PDF.

**Request:**
```json
{
  "patient_name": "John Doe",
  "medications": [
    {
      "name": "Lisinopril",
      "dosage": "10mg",
      "frequency": "Once daily"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Prescription created successfully",
  "prescription_id": "123"
}
```

#### GET /api/v1/prescriptions/<prescription_id>/download
Get presigned download URL.

**Response:**
```json
{
  "success": true,
  "download_url": "https://s3.amazonaws.com/..."
}
```

### Health Check Endpoint

#### GET /health
Check application health.

**Response:**
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

## Configuration

See `.env.example` for all configuration options.

### Required Configuration

- `AWS_REGION` - AWS region
- `AWS_COGNITO_USER_POOL_ID` - Cognito User Pool ID
- `AWS_COGNITO_CLIENT_ID` - Cognito App Client ID
- `S3_AUDIO_BUCKET` - S3 bucket for audio files
- `S3_PDF_BUCKET` - S3 bucket for PDFs
- `DB_SECRET_NAME` - Secrets Manager secret for database
- `FLASK_SECRET_NAME` - Secrets Manager secret for Flask
- `JWT_SECRET_NAME` - Secrets Manager secret for JWT

### Optional Configuration

- `AWS_COGNITO_CLIENT_SECRET` - Cognito App Client Secret
- `DATABASE_URL` - Fallback database URL
- `CORS_ALLOWED_ORIGINS` - CORS allowed origins
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

## Testing

### Manual Testing

1. Start the application:
   ```bash
   python app.py
   ```

2. Test authentication:
   ```bash
   # Register
   curl -X POST http://localhost:5000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "password": "Test123!", "name": "Test User"}'
   
   # Verify (use code from email)
   curl -X POST http://localhost:5000/api/v1/auth/verify \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "code": "123456"}'
   
   # Login
   curl -X POST http://localhost:5000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "password": "Test123!"}'
   ```

3. Test health check:
   ```bash
   curl http://localhost:5000/health
   ```

## Deployment

See `AWS_DEPLOYMENT.md` for detailed deployment instructions.

## Troubleshooting

### Common Issues

1. **Import errors** - Ensure all dependencies are installed: `pip install -r requirements.txt`
2. **AWS credentials** - Configure AWS CLI or set environment variables
3. **Database connection** - Verify RDS endpoint and credentials in Secrets Manager
4. **Cognito errors** - Check User Pool ID and Client ID configuration

### Debug Logging

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python app.py
```

## Security Considerations

1. **Never commit credentials** - Use environment variables or Secrets Manager
2. **Use HTTPS in production** - Configure SSL/TLS
3. **Validate all inputs** - File uploads, user inputs, etc.
4. **Implement rate limiting** - Prevent abuse
5. **Monitor CloudWatch logs** - Track suspicious activity
6. **Rotate secrets regularly** - Use AWS Secrets Manager rotation
7. **Follow least privilege** - Minimal IAM permissions

## Performance Optimization

1. **Connection pooling** - Database connections are pooled (2-10)
2. **Secret caching** - Secrets Manager responses are cached
3. **Retry logic** - Exponential backoff for transient failures
4. **Async operations** - Transcription jobs run asynchronously
5. **Presigned URLs** - Direct S3 downloads without proxy

## Future Enhancements

- [ ] Implement proper PDF generation library (ReportLab, WeasyPrint)
- [ ] Add batch transcription support
- [ ] Implement real-time transcription streaming
- [ ] Add prescription templates
- [ ] Implement audit logging
- [ ] Add metrics and monitoring dashboards
- [ ] Implement caching layer (Redis/ElastiCache)
- [ ] Add API rate limiting
- [ ] Implement WebSocket for real-time updates

## Support

For issues or questions:
- Check application logs
- Review AWS CloudWatch logs
- Verify IAM permissions
- Check AWS service quotas
