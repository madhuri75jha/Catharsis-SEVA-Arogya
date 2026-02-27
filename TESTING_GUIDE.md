# Testing Guide - SEVA Arogya AWS Integration

This guide provides comprehensive testing procedures for the AWS services integration.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Testing](#local-testing)
3. [API Testing](#api-testing)
4. [Integration Testing](#integration-testing)
5. [Load Testing](#load-testing)
6. [Security Testing](#security-testing)

## Prerequisites

### Required Tools

```bash
# Install testing tools
pip install pytest pytest-cov requests

# Install curl (if not already installed)
# Windows: choco install curl
# Mac: brew install curl
# Linux: apt-get install curl

# Optional: Install Postman or Insomnia for API testing
```

### Test Data

Create test files:

```bash
# Create sample audio file (or use your own)
# For testing, you can use any mp3/wav file under 16MB
```

## Local Testing

### 1. Start the Application

```bash
# Set environment variables
export LOG_LEVEL=DEBUG
export FLASK_DEBUG=True

# Start application
python app.py
```

Expected output:
```
 * Running on http://0.0.0.0:5000
 * Application initialized successfully
```

### 2. Health Check Test

```bash
curl http://localhost:5000/health
```

**Expected Response:**
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

**Failure Scenarios:**
- Database down: `"database": "unhealthy"`, HTTP 503
- Secrets Manager unavailable: `"secrets_manager": "unhealthy"`, HTTP 503

## API Testing

### Authentication Tests

#### Test 1: User Registration

```bash
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!",
    "name": "Test User"
  }'
```

**Expected Response (Success):**
```json
{
  "success": true,
  "message": "Registration successful. Please check your email for verification code.",
  "user_confirmed": false
}
```

**Expected Response (User Exists):**
```json
{
  "success": false,
  "message": "Registration failed. User may already exist or password does not meet requirements."
}
```

**Test Cases:**
- ✅ Valid email and password
- ✅ Duplicate email (should fail)
- ✅ Weak password (should fail)
- ✅ Invalid email format (should fail)
- ✅ Missing required fields (should fail)

#### Test 2: Email Verification

```bash
# Check your email for verification code
curl -X POST http://localhost:5000/api/v1/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "code": "123456"
  }'
```

**Expected Response (Success):**
```json
{
  "success": true,
  "message": "Account verified successfully. You can now login."
}
```

**Test Cases:**
- ✅ Valid verification code
- ✅ Invalid code (should fail)
- ✅ Expired code (should fail)
- ✅ Already verified user (should fail)

#### Test 3: User Login

```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{
    "email": "test@example.com",
    "password": "Test123!"
  }'
```

**Expected Response (Success):**
```json
{
  "success": true,
  "message": "Login successful"
}
```

**Test Cases:**
- ✅ Valid credentials
- ✅ Invalid password (should fail)
- ✅ Non-existent user (should fail)
- ✅ Unverified user (should fail)
- ✅ Session cookie set

#### Test 4: User Logout

```bash
curl -X POST http://localhost:5000/api/v1/auth/logout \
  -H "Content-Type: application/json" \
  -b cookies.txt
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Logout successful"
}
```

### Audio Upload Tests

#### Test 5: Audio File Upload

```bash
# Upload audio file
curl -X POST http://localhost:5000/api/v1/audio/upload \
  -b cookies.txt \
  -F "audio=@sample.mp3"
```

**Expected Response (Success):**
```json
{
  "success": true,
  "message": "Audio uploaded successfully",
  "s3_key": "audio/test@example.com/20240227_120000_sample.mp3"
}
```

**Test Cases:**
- ✅ Valid MP3 file
- ✅ Valid WAV file
- ✅ Valid FLAC file
- ✅ Invalid format (should fail)
- ✅ File too large >16MB (should fail)
- ✅ No file provided (should fail)
- ✅ Unauthenticated request (should fail)

### Transcription Tests

#### Test 6: Start Transcription

```bash
# Use S3 key from upload response
curl -X POST http://localhost:5000/api/v1/transcribe \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "s3_key": "audio/test@example.com/20240227_120000_sample.mp3"
  }'
```

**Expected Response (Success):**
```json
{
  "success": true,
  "message": "Transcription started",
  "job_id": "medical-transcription-abc-123-def-456"
}
```

**Test Cases:**
- ✅ Valid S3 key
- ✅ Invalid S3 key (should fail)
- ✅ Missing S3 key (should fail)
- ✅ Unauthenticated request (should fail)

#### Test 7: Check Transcription Status

```bash
# Use job_id from start transcription response
curl http://localhost:5000/api/v1/transcribe/status/medical-transcription-abc-123 \
  -b cookies.txt
```

**Expected Response (In Progress):**
```json
{
  "success": true,
  "status": "IN_PROGRESS",
  "job_id": "medical-transcription-abc-123"
}
```

**Expected Response (Completed):**
```json
{
  "success": true,
  "status": "COMPLETED",
  "job_id": "medical-transcription-abc-123"
}
```

**Test Cases:**
- ✅ Valid job ID
- ✅ Invalid job ID (should return 404)
- ✅ Status transitions (PENDING → IN_PROGRESS → COMPLETED)

#### Test 8: Get Transcription Result

```bash
# Wait for status to be COMPLETED
curl http://localhost:5000/api/v1/transcribe/result/medical-transcription-abc-123 \
  -b cookies.txt
```

**Expected Response (Success):**
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
        }
      ]
    }
  ],
  "categorized_entities": {
    "medications": [...],
    "conditions": [...],
    "procedures": []
  }
}
```

**Test Cases:**
- ✅ Completed transcription
- ✅ Transcription not ready (should return 404)
- ✅ Failed transcription (should return error)
- ✅ Entity extraction with confidence filtering

### Prescription Tests

#### Test 9: Create Prescription

```bash
curl -X POST http://localhost:5000/api/v1/prescriptions \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "patient_name": "John Doe",
    "medications": [
      {
        "name": "Lisinopril",
        "dosage": "10mg",
        "frequency": "Once daily"
      },
      {
        "name": "Metformin",
        "dosage": "500mg",
        "frequency": "Twice daily"
      }
    ]
  }'
```

**Expected Response (Success):**
```json
{
  "success": true,
  "message": "Prescription created successfully",
  "prescription_id": "123"
}
```

**Test Cases:**
- ✅ Valid prescription data
- ✅ Missing patient name (should fail)
- ✅ Empty medications (should fail)
- ✅ PDF upload to S3
- ✅ Database record created

#### Test 10: Download Prescription

```bash
# Use prescription_id from create response
curl http://localhost:5000/api/v1/prescriptions/123/download \
  -b cookies.txt
```

**Expected Response (Success):**
```json
{
  "success": true,
  "download_url": "https://s3.amazonaws.com/seva-arogya-pdf/prescriptions/test@example.com/123.pdf?..."
}
```

**Test Cases:**
- ✅ Valid prescription ID
- ✅ Invalid prescription ID (should return 404)
- ✅ Unauthorized access (different user, should return 403)
- ✅ Presigned URL expires after 1 hour

## Integration Testing

### End-to-End Workflow Test

```bash
#!/bin/bash
# Complete workflow test script

echo "1. Register user"
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"workflow@test.com","password":"Test123!","name":"Workflow Test"}'

echo "\n2. Verify user (manual step - check email)"
read -p "Enter verification code: " CODE
curl -X POST http://localhost:5000/api/v1/auth/verify \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"workflow@test.com\",\"code\":\"$CODE\"}"

echo "\n3. Login"
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"email":"workflow@test.com","password":"Test123!"}'

echo "\n4. Upload audio"
UPLOAD_RESPONSE=$(curl -X POST http://localhost:5000/api/v1/audio/upload \
  -b cookies.txt \
  -F "audio=@sample.mp3")
S3_KEY=$(echo $UPLOAD_RESPONSE | jq -r '.s3_key')
echo "S3 Key: $S3_KEY"

echo "\n5. Start transcription"
TRANSCRIBE_RESPONSE=$(curl -X POST http://localhost:5000/api/v1/transcribe \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d "{\"s3_key\":\"$S3_KEY\"}")
JOB_ID=$(echo $TRANSCRIBE_RESPONSE | jq -r '.job_id')
echo "Job ID: $JOB_ID"

echo "\n6. Poll for completion"
while true; do
  STATUS_RESPONSE=$(curl -s http://localhost:5000/api/v1/transcribe/status/$JOB_ID -b cookies.txt)
  STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "COMPLETED" ]; then
    break
  fi
  
  sleep 5
done

echo "\n7. Get transcript and entities"
curl http://localhost:5000/api/v1/transcribe/result/$JOB_ID \
  -b cookies.txt | jq '.'

echo "\n8. Create prescription"
PRESCRIPTION_RESPONSE=$(curl -X POST http://localhost:5000/api/v1/prescriptions \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"patient_name":"John Doe","medications":[{"name":"Lisinopril","dosage":"10mg","frequency":"Once daily"}]}')
PRESCRIPTION_ID=$(echo $PRESCRIPTION_RESPONSE | jq -r '.prescription_id')
echo "Prescription ID: $PRESCRIPTION_ID"

echo "\n9. Get download URL"
curl http://localhost:5000/api/v1/prescriptions/$PRESCRIPTION_ID/download \
  -b cookies.txt | jq '.'

echo "\n10. Logout"
curl -X POST http://localhost:5000/api/v1/auth/logout \
  -b cookies.txt

echo "\nWorkflow test complete!"
```

## Load Testing

### Using Apache Bench

```bash
# Test health endpoint
ab -n 1000 -c 10 http://localhost:5000/health

# Test login endpoint
ab -n 100 -c 5 -p login.json -T application/json http://localhost:5000/api/v1/auth/login
```

### Using Locust

Create `locustfile.py`:

```python
from locust import HttpUser, task, between

class SevaArogyaUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login
        response = self.client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "Test123!"
        })
    
    @task(3)
    def health_check(self):
        self.client.get("/health")
    
    @task(1)
    def upload_audio(self):
        with open("sample.mp3", "rb") as f:
            self.client.post("/api/v1/audio/upload", files={"audio": f})
```

Run load test:
```bash
locust -f locustfile.py --host=http://localhost:5000
```

## Security Testing

### 1. Authentication Tests

```bash
# Test without authentication
curl http://localhost:5000/api/v1/audio/upload
# Expected: Redirect to login or 401

# Test with invalid token
curl http://localhost:5000/api/v1/audio/upload \
  -H "Cookie: session=invalid"
# Expected: Redirect to login or 401

# Test token expiration
# Wait for token to expire (default 1 hour)
# Expected: Token refresh or redirect to login
```

### 2. Input Validation Tests

```bash
# SQL injection attempt
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"' OR '1'='1"}'
# Expected: Login fails, no SQL injection

# XSS attempt
curl -X POST http://localhost:5000/api/v1/prescriptions \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"patient_name":"<script>alert(1)</script>","medications":[]}'
# Expected: Input sanitized or rejected

# File upload validation
curl -X POST http://localhost:5000/api/v1/audio/upload \
  -b cookies.txt \
  -F "audio=@malicious.exe"
# Expected: File rejected (invalid format)
```

### 3. CORS Tests

```bash
# Test CORS headers
curl -H "Origin: http://evil.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -X OPTIONS \
  http://localhost:5000/api/v1/auth/login
# Expected: CORS headers only for allowed origins
```

## Automated Testing

### Unit Tests

Create `tests/test_auth.py`:

```python
import pytest
from aws_services.auth_manager import AuthManager

def test_auth_manager_initialization():
    auth_manager = AuthManager(
        region='ap-south-1',
        user_pool_id='test-pool',
        client_id='test-client'
    )
    assert auth_manager.user_pool_id == 'test-pool'
    assert auth_manager.client_id == 'test-client'

# Add more tests...
```

Run tests:
```bash
pytest tests/ -v --cov=aws_services --cov=models --cov=utils
```

## Test Results Documentation

### Test Report Template

```markdown
# Test Report - SEVA Arogya AWS Integration

**Date**: YYYY-MM-DD
**Tester**: Name
**Environment**: Local/Staging/Production

## Summary
- Total Tests: X
- Passed: X
- Failed: X
- Skipped: X

## Test Results

### Authentication
- [ ] User Registration: PASS/FAIL
- [ ] Email Verification: PASS/FAIL
- [ ] User Login: PASS/FAIL
- [ ] Token Refresh: PASS/FAIL
- [ ] User Logout: PASS/FAIL

### Audio & Transcription
- [ ] Audio Upload: PASS/FAIL
- [ ] Start Transcription: PASS/FAIL
- [ ] Check Status: PASS/FAIL
- [ ] Get Results: PASS/FAIL
- [ ] Entity Extraction: PASS/FAIL

### Prescriptions
- [ ] Create Prescription: PASS/FAIL
- [ ] Download Prescription: PASS/FAIL

### Security
- [ ] Authentication Required: PASS/FAIL
- [ ] Input Validation: PASS/FAIL
- [ ] CORS Configuration: PASS/FAIL

## Issues Found
1. Issue description
   - Severity: High/Medium/Low
   - Steps to reproduce
   - Expected vs Actual behavior

## Recommendations
- List of improvements or fixes needed
```

## Troubleshooting

### Common Test Failures

1. **Health check fails**
   - Check database connection
   - Verify Secrets Manager access
   - Check AWS credentials

2. **Authentication fails**
   - Verify Cognito User Pool ID
   - Check Cognito Client ID
   - Ensure user is verified

3. **Transcription fails**
   - Check S3 bucket permissions
   - Verify audio file format
   - Check Transcribe service quotas

4. **Entity extraction returns empty**
   - Verify transcript contains medical text
   - Check confidence threshold (0.5)
   - Review Comprehend Medical permissions

## Next Steps

After completing tests:
1. Document all test results
2. Fix any identified issues
3. Re-test failed scenarios
4. Update test cases as needed
5. Proceed to deployment

---

**Note**: Always test in a non-production environment first!
