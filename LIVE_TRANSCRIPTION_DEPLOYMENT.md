# Live Audio Transcription Streaming - Deployment Guide

## Overview

This guide covers the deployment of the live audio transcription streaming feature for SEVA Arogya. The feature enables real-time audio capture, streaming to AWS Transcribe Medical, and live display of transcription results.

## Prerequisites

### Infrastructure Requirements
- AWS Account with appropriate permissions
- Terraform >= 1.0
- Python 3.9+
- Node.js (for frontend dependencies via CDN)

### AWS Services Used
- **AWS Transcribe Medical**: Real-time speech-to-text transcription
- **Amazon S3**: Audio file storage
- **Amazon RDS (PostgreSQL)**: Transcription metadata storage
- **AWS ECS (Fargate)**: Container hosting
- **Application Load Balancer**: Traffic routing
- **AWS Secrets Manager**: Credentials management

## Deployment Steps

### 1. Update Infrastructure with Terraform

Navigate to the infrastructure directory:
```bash
cd seva-arogya-infra
```

Initialize Terraform (if not already done):
```bash
terraform init
```

Review the changes:
```bash
terraform plan
```

Apply the infrastructure changes:
```bash
terraform apply
```

**Changes Applied:**
- IAM policies for AWS Transcribe streaming permissions
- Environment variable `AWS_TRANSCRIBE_REGION` added to ECS task definition
- Outputs for Transcribe service endpoints

### 2. Database Migrations (Automatic)

Database migrations now run automatically on application startup. The application will:
1. Check for pending migrations in the `migrations/` directory
2. Apply any unapplied migrations in order
3. Track applied migrations in the `schema_migrations` table

**No manual intervention required!** The migration will run when the container starts.

**To verify migrations were applied:**
```bash
# Check application logs
aws logs tail /ecs/seva-arogya-dev --follow --filter-pattern "migration" --region us-east-1

# Or check the health endpoint
curl https://your-alb-url.amazonaws.com/health
```

The health check response includes migration status:
```json
{
  "status": "healthy",
  "checks": {
    "migrations": {
      "status": "up_to_date",
      "applied": 1,
      "pending": 0
    }
  }
}
```

**Manual migration (if needed):**
If you need to run migrations manually:
```bash
python migrations/run_migration.py migrations/001_add_streaming_columns.sql
```

### 3. Install Python Dependencies

Update your Python environment with new dependencies:
```bash
pip install -r requirements.txt
```

**New Dependencies:**
- `flask-socketio==5.3.4` - WebSocket support
- `eventlet==0.33.3` - Async worker for SocketIO
- `amazon-transcribe==0.6.2` - AWS Transcribe streaming client
- `pydub==0.25.1` - Audio format conversion

**Note:** `pydub` requires `ffmpeg` to be installed on the system:
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### 4. Update Environment Variables

Add the following environment variable to your `.env` file:
```bash
AWS_TRANSCRIBE_REGION=us-east-1  # Or your preferred region
```

The variable is automatically added to ECS task definition by Terraform.

### 5. Build and Deploy Docker Image

Build the Docker image:
```bash
docker build -t seva-arogya-backend:latest .
```

Tag for ECR:
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

docker tag seva-arogya-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/seva-arogya-dev-backend:latest
```

Push to ECR:
```bash
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/seva-arogya-dev-backend:latest
```

### 6. Update ECS Service

Force new deployment to use the updated image:
```bash
aws ecs update-service \
  --cluster seva-arogya-dev-cluster \
  --service seva-arogya-dev-service \
  --force-new-deployment \
  --region us-east-1
```

### 7. Verify Deployment

Check ECS service status:
```bash
aws ecs describe-services \
  --cluster seva-arogya-dev-cluster \
  --services seva-arogya-dev-service \
  --region us-east-1
```

Check application logs:
```bash
aws logs tail /ecs/seva-arogya-dev --follow --region us-east-1
```

## Configuration

### Audio Quality Settings

The feature supports three quality levels:

| Quality | Sample Rate | Bandwidth | Use Case |
|---------|-------------|-----------|----------|
| Low | 8kHz | ~16 kbps | Low bandwidth, basic transcription |
| Medium | 16kHz | ~32 kbps | **Recommended** - Good balance |
| High | 48kHz | ~96 kbps | Best quality, high bandwidth |

Configure in the UI or set default in `live_transcription.html`.

### Session Limits

- **Maximum concurrent sessions**: 100 per server instance
- **Idle timeout**: 5 minutes
- **Maximum recording duration**: 30 minutes
- **Maximum audio buffer**: 60MB (~30 minutes at 16kHz)

Adjust in `socketio_handlers.py`:
```python
session_manager = SessionManager(max_sessions=100, idle_timeout=300)
```

### WebSocket Configuration

Configure in `app.py`:
```python
socketio = SocketIO(
    app,
    cors_allowed_origins=cors_origins,
    async_mode='eventlet',
    ping_timeout=60,        # Connection timeout
    ping_interval=25,       # Heartbeat interval
    max_http_buffer_size=1024 * 1024  # 1MB max message
)
```

## Monitoring

### Key Metrics to Monitor

1. **Active Sessions**: Number of concurrent streaming sessions
2. **Session Duration**: Average and max session duration
3. **Audio Upload Success Rate**: S3 upload success/failure ratio
4. **Transcription Latency**: Time from speech to display
5. **Error Rates**: WebSocket errors, Transcribe errors, S3 errors

### CloudWatch Logs

Monitor application logs:
```bash
aws logs tail /ecs/seva-arogya-dev --follow --filter-pattern "ERROR" --region us-east-1
```

Search for specific events:
```bash
# Session events
aws logs filter-log-events \
  --log-group-name /ecs/seva-arogya-dev \
  --filter-pattern "Session" \
  --region us-east-1

# Transcription errors
aws logs filter-log-events \
  --log-group-name /ecs/seva-arogya-dev \
  --filter-pattern "Transcribe" \
  --region us-east-1
```

### Health Checks

The application includes a health check endpoint:
```bash
curl https://your-alb-url.amazonaws.com/health
```

Response includes:
- Database connectivity
- Secrets Manager connectivity
- Overall health status

## Troubleshooting

### Common Issues

#### 1. WebSocket Connection Fails

**Symptoms**: "Connection lost" error in UI

**Causes**:
- Load balancer not configured for WebSocket
- CORS configuration incorrect
- Network firewall blocking WebSocket

**Solutions**:
- Verify ALB target group has WebSocket support enabled
- Check CORS origins in environment variables
- Test with browser developer tools (Network tab)

#### 2. Audio Not Streaming

**Symptoms**: No transcription results appear

**Causes**:
- Microphone permissions denied
- AWS Transcribe permissions missing
- Audio format incompatible

**Solutions**:
- Check browser console for permission errors
- Verify IAM role has `transcribe:StartMedicalStreamTranscription`
- Test with different audio quality settings

#### 3. S3 Upload Failures

**Symptoms**: "Failed to save audio file" error

**Causes**:
- S3 bucket permissions incorrect
- Network timeout
- Audio file too large

**Solutions**:
- Verify ECS task role has S3 PutObject permission
- Check S3 bucket policy
- Review CloudWatch logs for detailed error

#### 4. Database Connection Issues

**Symptoms**: Transcription records not saved

**Causes**:
- RDS security group blocking ECS
- Database credentials incorrect
- Migration not applied

**Solutions**:
- Verify RDS security group allows ECS security group
- Check Secrets Manager credentials
- Run database migration script

### Debug Mode

Enable debug logging:
```bash
# In .env
LOG_LEVEL=DEBUG
```

Restart the application to apply changes.

### Testing Locally

Run the application locally for testing:
```bash
# Set up environment
cp .env.example .env
# Edit .env with your AWS credentials

# Run migration
python migrations/run_migration.py migrations/001_add_streaming_columns.sql

# Start application
python app.py
```

Access at: http://localhost:5000/live-transcription

## Security Considerations

### Authentication
- All WebSocket connections require Flask session authentication
- Sessions validated on connection and during streaming

### Data Protection
- Audio files encrypted at rest in S3 (AES-256)
- Database connections use SSL/TLS
- Transcription data includes PHI - ensure HIPAA compliance

### Network Security
- Use HTTPS/WSS in production
- Configure ALB with SSL certificate
- Restrict CORS origins to known domains

### IAM Permissions
- Follow principle of least privilege
- ECS task role has minimal required permissions
- Regularly audit IAM policies

## Rollback Procedure

If issues occur after deployment:

1. **Rollback ECS Service**:
```bash
aws ecs update-service \
  --cluster seva-arogya-dev-cluster \
  --service seva-arogya-dev-service \
  --task-definition seva-arogya-dev-task:PREVIOUS_REVISION \
  --region us-east-1
```

2. **Rollback Database** (if needed):
```sql
-- See migrations/001_add_streaming_columns_rollback.sql
ALTER TABLE transcriptions
DROP COLUMN IF EXISTS session_id,
-- ... (see rollback script)
```

3. **Rollback Terraform** (if needed):
```bash
cd seva-arogya-infra
git checkout HEAD~1 -- main.tf modules/iam/main.tf
terraform apply
```

## Performance Tuning

### Optimize for High Load

1. **Increase ECS Task Count**:
```bash
aws ecs update-service \
  --cluster seva-arogya-dev-cluster \
  --service seva-arogya-dev-service \
  --desired-count 3 \
  --region us-east-1
```

2. **Adjust Session Limits**:
```python
# In socketio_handlers.py
session_manager = SessionManager(max_sessions=200, idle_timeout=300)
```

3. **Enable Auto Scaling**:
Configure ECS service auto-scaling based on CPU/memory metrics.

### Optimize for Low Latency

1. **Use Regional Endpoints**: Deploy in region closest to users
2. **Reduce Audio Chunk Size**: Smaller chunks = lower latency (but more overhead)
3. **Optimize Network**: Use CloudFront for static assets

## Support

For issues or questions:
- Check CloudWatch logs first
- Review this documentation
- Contact DevOps team with log excerpts and error messages

## Next Steps

After successful deployment:
1. Test with real users in staging environment
2. Monitor metrics for 24-48 hours
3. Gradually roll out to production
4. Set up alerts for error rates and latency
5. Document any environment-specific configurations
