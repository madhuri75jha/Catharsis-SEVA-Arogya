# Quick Start Guide - AWS Integration

Get the SEVA Arogya application running with AWS services in minutes.

## Prerequisites

- Python 3.8+
- AWS Account
- AWS CLI configured
- PostgreSQL database (local or RDS)

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Configure AWS Credentials

### Option A: AWS CLI (Recommended for local development)
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter your default region (e.g., ap-south-1)
```

### Option B: Environment Variables
```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=ap-south-1
```

## Step 3: Set Up AWS Resources

### Create Cognito User Pool

```bash
# Create User Pool
aws cognito-idp create-user-pool \
  --pool-name seva-arogya-users \
  --policies "PasswordPolicy={MinimumLength=8,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true}" \
  --auto-verified-attributes email

# Note the UserPoolId from the output

# Create App Client
aws cognito-idp create-user-pool-client \
  --user-pool-id YOUR_USER_POOL_ID \
  --client-name seva-arogya-client \
  --explicit-auth-flows USER_PASSWORD_AUTH

# Note the ClientId from the output
```

### Create S3 Buckets

```bash
# Audio bucket
aws s3 mb s3://seva-arogya-audio-YOUR_UNIQUE_ID --region ap-south-1

# PDF bucket
aws s3 mb s3://seva-arogya-pdf-YOUR_UNIQUE_ID --region ap-south-1

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket seva-arogya-audio-YOUR_UNIQUE_ID \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

aws s3api put-bucket-encryption \
  --bucket seva-arogya-pdf-YOUR_UNIQUE_ID \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

### Create Secrets in Secrets Manager (Optional)

```bash
# Database credentials
aws secretsmanager create-secret \
  --name seva-arogya/db-credentials \
  --secret-string '{"host":"localhost","port":5432,"database":"seva_arogya","username":"postgres","password":"your-password"}'

# Flask secret key
aws secretsmanager create-secret \
  --name seva-arogya/flask-secret \
  --secret-string "$(openssl rand -base64 32)"

# JWT secret
aws secretsmanager create-secret \
  --name seva-arogya/jwt-secret \
  --secret-string "$(openssl rand -base64 32)"
```

## Step 4: Configure Environment Variables

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
# AWS Configuration
AWS_REGION=ap-south-1

# AWS Cognito
AWS_COGNITO_USER_POOL_ID=ap-south-1_xxxxxxxxx
AWS_COGNITO_CLIENT_ID=your-client-id

# AWS S3 Buckets
S3_AUDIO_BUCKET=seva-arogya-audio-YOUR_UNIQUE_ID
S3_PDF_BUCKET=seva-arogya-pdf-YOUR_UNIQUE_ID

# AWS Secrets Manager (optional - can use DATABASE_URL instead)
DB_SECRET_NAME=seva-arogya/db-credentials
FLASK_SECRET_NAME=seva-arogya/flask-secret
JWT_SECRET_NAME=seva-arogya/jwt-secret

# Database Configuration (fallback if not using Secrets Manager)
DATABASE_URL=postgresql://postgres:password@localhost:5432/seva_arogya

# CORS Configuration
CORS_ALLOWED_ORIGINS=http://localhost:5000,http://localhost:3000

# Logging
LOG_LEVEL=INFO
```

## Step 5: Set Up Database

### Create Database

```bash
# Using psql
createdb seva_arogya

# Or using SQL
psql -U postgres -c "CREATE DATABASE seva_arogya;"
```

The application will automatically create tables on startup.

## Step 6: Run the Application

```bash
python app.py
```

You should see:
```
 * Running on http://0.0.0.0:5000
 * Application initialized successfully
```

## Step 7: Test the Application

### Test Health Check

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

### Test Registration

```bash
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!",
    "name": "Test User"
  }'
```

### Test Login

```bash
# First, verify your email using the code sent to your email
curl -X POST http://localhost:5000/api/v1/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "code": "123456"
  }'

# Then login
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!"
  }'
```

### Test Audio Upload

```bash
# Save session cookie from login response
curl -X POST http://localhost:5000/api/v1/audio/upload \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -F "audio=@sample.mp3"
```

## Troubleshooting

### Issue: "Required configuration validation failed"

**Solution:** Check that all required environment variables are set in `.env`:
- AWS_REGION
- AWS_COGNITO_USER_POOL_ID
- AWS_COGNITO_CLIENT_ID
- S3_AUDIO_BUCKET
- S3_PDF_BUCKET
- DATABASE_URL or DB_SECRET_NAME

### Issue: "Database health check failed"

**Solution:** 
1. Verify PostgreSQL is running: `pg_isready`
2. Check DATABASE_URL is correct
3. Ensure database exists: `psql -l | grep seva_arogya`
4. Check database credentials

### Issue: "AccessDeniedException" from AWS

**Solution:**
1. Verify AWS credentials: `aws sts get-caller-identity`
2. Check IAM permissions for:
   - cognito-idp:*
   - s3:PutObject, s3:GetObject
   - transcribe:StartMedicalTranscriptionJob
   - comprehendmedical:DetectEntitiesV2
   - secretsmanager:GetSecretValue

### Issue: "Invalid credentials" on login

**Solution:**
1. Verify user is confirmed in Cognito
2. Check Cognito User Pool ID and Client ID
3. Ensure password meets requirements (8+ chars, uppercase, lowercase, number)

### Issue: "Failed to upload audio file"

**Solution:**
1. Check S3 bucket exists: `aws s3 ls | grep seva-arogya`
2. Verify S3 bucket permissions
3. Ensure file format is supported (wav, mp3, flac, mp4)
4. Check file size is under 16MB

## Quick Commands Reference

```bash
# Start application
python app.py

# Check health
curl http://localhost:5000/health

# View logs (if using systemd)
journalctl -u seva-arogya -f

# Check AWS credentials
aws sts get-caller-identity

# List S3 buckets
aws s3 ls

# List Cognito User Pools
aws cognito-idp list-user-pools --max-results 10

# Check database connection
psql -U postgres -d seva_arogya -c "SELECT 1;"

# View application logs
tail -f app.log  # if logging to file

# Test with debug logging
LOG_LEVEL=DEBUG python app.py
```

## Next Steps

1. **Test all endpoints** - Use the API reference in AWS_INTEGRATION_README.md
2. **Upload sample audio** - Test transcription with medical audio files
3. **Create prescriptions** - Test the full workflow
4. **Monitor logs** - Check CloudWatch or local logs for errors
5. **Deploy to production** - Follow AWS_DEPLOYMENT.md for ECS deployment

## Development Tips

### Enable Debug Mode

```bash
export FLASK_DEBUG=True
export LOG_LEVEL=DEBUG
python app.py
```

### Use Local Database

For faster development, use local PostgreSQL instead of RDS:

```bash
# .env
DATABASE_URL=postgresql://postgres:password@localhost:5432/seva_arogya
```

### Skip Secrets Manager

For local development, you can skip Secrets Manager and use environment variables:

```bash
# .env
SECRET_KEY=your-local-secret-key
DATABASE_URL=postgresql://postgres:password@localhost:5432/seva_arogya
# Don't set DB_SECRET_NAME, FLASK_SECRET_NAME, JWT_SECRET_NAME
```

### Test Without AWS Services

To test the application structure without AWS:
1. Comment out AWS service initialization in `app.py`
2. Use mock objects for testing
3. Focus on route logic and database operations

## Resources

- **Full Documentation**: See AWS_INTEGRATION_README.md
- **Deployment Guide**: See AWS_DEPLOYMENT.md
- **API Reference**: See AWS_INTEGRATION_README.md#api-reference
- **Troubleshooting**: See AWS_DEPLOYMENT.md#troubleshooting

## Support

If you encounter issues:
1. Check application logs
2. Verify AWS credentials and permissions
3. Review environment variables
4. Check AWS service quotas
5. Consult AWS documentation

Happy coding! 🚀
