# SEVA Arogya - Complete Testing Guide

**Version:** 2.0  
**Last Updated:** March 8, 2026

---

## 📋 Table of Contents

1. [Testing Overview](#testing-overview)
2. [Quick Tests](#quick-tests)
3. [Unit Testing](#unit-testing)
4. [Integration Testing](#integration-testing)
5. [API Testing](#api-testing)
6. [Property-Based Testing](#property-based-testing)
7. [Load Testing](#load-testing)
8. [Security Testing](#security-testing)
9. [End-to-End Testing](#end-to-end-testing)

---

## 1. Testing Overview

### Testing Strategy

| Test Type | Coverage | Purpose |
|-----------|----------|---------|
| **Unit Tests** | 70% | Individual components |
| **Integration Tests** | 20% | Service interactions |
| **E2E Tests** | 10% | Complete workflows |
| **Property Tests** | Critical paths | Correctness validation |

### Test Environments

- **Local:** Development and unit testing
- **Staging:** Integration and E2E testing
- **Production:** Smoke tests only

---

## 2. Quick Tests

### Health Checks

```bash
# Basic health
curl http://localhost:5000/health

# Expected response
{
  "status": "healthy",
  "timestamp": 1234567890.123,
  "checks": {
    "database": "healthy",
    "secrets_manager": "healthy"
  }
}

# AWS connectivity
curl http://localhost:5000/health/aws-connectivity

# Expected response
{
  "status": "healthy",
  "services": {
    "cognito": {"status": "healthy", "latency_ms": 45},
    "s3": {"status": "healthy", "latency_ms": 23},
    "transcribe": {"status": "healthy", "latency_ms": 67},
    "comprehend": {"status": "healthy", "latency_ms": 89},
    "bedrock": {"status": "healthy", "latency_ms": 120},
    "secrets_manager": {"status": "healthy", "latency_ms": 34}
  }
}
```

### AWS Connectivity Test

```bash
python test_aws_connectivity.py
```

**Expected output:**
```
✅ DNS Resolution: PASS
✅ HTTP Connectivity: PASS
✅ AWS Credentials: PASS
✅ Cognito Client: PASS
✅ S3 Client: PASS
✅ Transcribe Client: PASS
✅ Comprehend Client: PASS
✅ Bedrock Client: PASS
✅ Secrets Manager Client: PASS

All checks passed! ✅
```

---

## 3. Unit Testing

### Run Unit Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=aws_services --cov=models --cov=services --cov-report=html

# Specific test file
pytest tests/test_prescription_service.py -v

# Specific test
pytest tests/test_prescription_service.py::test_create_prescription -v
```

### Test Structure

```
tests/
├── test_auth_manager.py
├── test_transcribe_manager.py
├── test_comprehend_manager.py
├── test_bedrock_client.py
├── test_prescription_service.py
├── test_rbac_service.py
├── test_pdf_generator.py
└── property_tests/
    ├── test_prescription_state_machine.py
    └── test_section_approval.py
```

### Example Unit Test

```python
import pytest
from services.prescription_service import PrescriptionService

def test_create_prescription(db_manager):
    service = PrescriptionService(db_manager)
    
    prescription_id = service.create_prescription(
        user_id="doctor@hospital.com",
        hospital_id="hosp_123",
        patient_name="John Doe"
    )
    
    assert prescription_id is not None
    
    prescription = service.get_prescription(prescription_id, "doctor@hospital.com")
    assert prescription['state'] == 'Draft'
    assert prescription['patient_name'] == 'John Doe'
```

---

## 4. Integration Testing

### AWS Service Integration Tests

```bash
# Test Cognito integration
python tests/test_cognito_integration.py

# Test Transcribe integration
python tests/test_transcribe_integration.py

# Test Bedrock integration
python tests/test_bedrock_integration.py
```

### Database Integration Tests

```python
import pytest
from aws_services.database_manager import DatabaseManager

def test_database_connection():
    db = DatabaseManager(credentials)
    assert db.health_check() == True

def test_prescription_crud():
    # Create
    prescription_id = db.execute_with_retry(
        "INSERT INTO prescriptions (patient_name, state) VALUES (%s, %s) RETURNING prescription_id",
        ("Test Patient", "Draft")
    )[0][0]
    
    # Read
    result = db.execute_with_retry(
        "SELECT patient_name, state FROM prescriptions WHERE prescription_id = %s",
        (prescription_id,)
    )
    assert result[0] == ("Test Patient", "Draft")
    
    # Update
    db.execute_with_retry(
        "UPDATE prescriptions SET state = %s WHERE prescription_id = %s",
        ("InProgress", prescription_id)
    )
    
    # Delete
    db.execute_with_retry(
        "DELETE FROM prescriptions WHERE prescription_id = %s",
        (prescription_id,)
    )
```

---

## 5. API Testing

### Authentication Flow

```bash
# 1. Register
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!","name":"Test User"}'

# 2. Verify (check email for code)
curl -X POST http://localhost:5000/api/v1/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","code":"123456"}'

# 3. Login
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"email":"test@example.com","password":"Test123!"}'

# 4. Access protected endpoint
curl http://localhost:5000/api/v1/profile -b cookies.txt
```

### Transcription Flow

```bash
# 1. Upload audio
curl -X POST http://localhost:5000/api/v1/audio/upload \
  -b cookies.txt \
  -F "audio=@sample.mp3"

# Response: {"success": true, "s3_key": "audio/..."}

# 2. Start transcription
curl -X POST http://localhost:5000/api/v1/transcribe \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"s3_key":"audio/test@example.com/sample.mp3"}'

# Response: {"success": true, "job_id": "medical-transcription-..."}

# 3. Check status
curl http://localhost:5000/api/v1/transcribe/status/<job_id> -b cookies.txt

# 4. Get results
curl http://localhost:5000/api/v1/transcribe/result/<job_id> -b cookies.txt
```

### Prescription Workflow

```bash
# 1. Create prescription (Draft)
curl -X POST http://localhost:5000/api/v1/prescriptions \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"patient_name":"John Doe","hospital_id":"hosp_123"}'

# Response: {"success": true, "prescription_id": "123"}

# 2. Transition to InProgress (AI extraction)
curl -X POST http://localhost:5000/api/v1/prescriptions/123/transition-to-in-progress \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"transcript":"Patient has fever and cough. Prescribed paracetamol 500mg."}'

# 3. Approve section
curl -X POST http://localhost:5000/api/v1/prescriptions/123/sections/diagnosis/approve \
  -b cookies.txt

# 4. Reject section (enables editing)
curl -X POST http://localhost:5000/api/v1/prescriptions/123/sections/medications/reject \
  -b cookies.txt

# 5. Update rejected section
curl -X PUT http://localhost:5000/api/v1/prescriptions/123/sections/medications \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"content":"Updated medication list"}'

# 6. Finalize prescription
curl -X POST http://localhost:5000/api/v1/prescriptions/123/finalize \
  -b cookies.txt

# 7. Generate PDF
curl -X POST http://localhost:5000/api/v1/prescriptions/123/pdf \
  -b cookies.txt

# 8. Soft delete
curl -X DELETE http://localhost:5000/api/v1/prescriptions/123 \
  -b cookies.txt

# 9. Restore
curl -X POST http://localhost:5000/api/v1/prescriptions/123/restore \
  -b cookies.txt
```

---

## 6. Property-Based Testing

### Using Hypothesis

```python
from hypothesis import given, strategies as st
from services.prescription_service import PrescriptionService

@given(
    patient_name=st.text(min_size=1, max_size=100),
    state=st.sampled_from(['Draft', 'InProgress', 'Finalized'])
)
def test_prescription_state_transitions(patient_name, state):
    """Property: State transitions must follow valid paths"""
    service = PrescriptionService(db_manager)
    
    # Create prescription
    prescription_id = service.create_prescription(
        user_id="test@example.com",
        hospital_id="hosp_123",
        patient_name=patient_name
    )
    
    # Verify initial state
    prescription = service.get_prescription(prescription_id, "test@example.com")
    assert prescription['state'] == 'Draft'
    
    # Test valid transitions
    if state == 'InProgress':
        result = service.transition_to_in_progress(prescription_id, "test@example.com", {})
        assert result['success'] == True
    
    # Test invalid transitions
    with pytest.raises(ValueError):
        service.finalize_prescription(prescription_id, "test@example.com")  # Can't finalize from Draft
```

### Run Property Tests

```bash
pytest tests/property_tests/ -v --hypothesis-show-statistics
```

---

## 7. Load Testing

### Using Locust

Create `locustfile.py`:

```python
from locust import HttpUser, task, between
import json

class SevaArogyaUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login
        response = self.client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "Test123!"
        })
        self.token = response.cookies.get('session')
    
    @task(3)
    def health_check(self):
        self.client.get("/health")
    
    @task(2)
    def list_prescriptions(self):
        self.client.get("/api/v1/prescriptions")
    
    @task(1)
    def create_prescription(self):
        self.client.post("/api/v1/prescriptions", json={
            "patient_name": "Load Test Patient",
            "hospital_id": "hosp_123"
        })
```

Run load test:
```bash
# Install locust
pip install locust

# Run test
locust -f locustfile.py --host=http://localhost:5000

# Open browser to http://localhost:8089
# Set users: 50, spawn rate: 10
```

### Performance Targets

| Metric | Target | Test Command |
|--------|--------|--------------|
| API Response | < 500ms | `ab -n 1000 -c 10 http://localhost:5000/health` |
| Transcription | < 2s | Manual timing |
| AI Extraction | < 3s | Manual timing |
| PDF Generation | < 5s | Manual timing |
| Concurrent Users | 500+ | Locust load test |

---

## 8. Security Testing

### Authentication Tests

```bash
# Test without authentication
curl http://localhost:5000/api/v1/prescriptions
# Expected: 401 Unauthorized or redirect

# Test with invalid token
curl http://localhost:5000/api/v1/prescriptions \
  -H "Cookie: session=invalid"
# Expected: 401 Unauthorized

# Test token expiration
# Wait for token to expire (1 hour)
# Expected: Token refresh or 401
```

### Input Validation Tests

```bash
# SQL injection attempt
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"'\'' OR '\''1'\''='\''1"}'
# Expected: Login fails, no SQL injection

# XSS attempt
curl -X POST http://localhost:5000/api/v1/prescriptions \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"patient_name":"<script>alert(1)</script>"}'
# Expected: Input sanitized or rejected

# File upload validation
curl -X POST http://localhost:5000/api/v1/audio/upload \
  -b cookies.txt \
  -F "audio=@malicious.exe"
# Expected: File rejected (invalid format)

# Oversized file
curl -X POST http://localhost:5000/api/v1/audio/upload \
  -b cookies.txt \
  -F "audio=@large_file.mp3"  # > 16MB
# Expected: 413 Request Entity Too Large
```

### Authorization Tests

```bash
# Test cross-user access
# Login as user1
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -c user1_cookies.txt \
  -d '{"email":"user1@example.com","password":"Pass123!"}'

# Create prescription as user1
curl -X POST http://localhost:5000/api/v1/prescriptions \
  -H "Content-Type: application/json" \
  -b user1_cookies.txt \
  -d '{"patient_name":"Test"}' \
  | jq -r '.prescription_id' > prescription_id.txt

# Login as user2
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -c user2_cookies.txt \
  -d '{"email":"user2@example.com","password":"Pass123!"}'

# Try to access user1's prescription as user2
curl http://localhost:5000/api/v1/prescriptions/$(cat prescription_id.txt) \
  -b user2_cookies.txt
# Expected: 403 Forbidden or 404 Not Found
```

---

## 9. End-to-End Testing

### Complete Workflow Test Script

```bash
#!/bin/bash
# e2e_test.sh - Complete workflow test

set -e

echo "🧪 Starting E2E Test"

# 1. Register
echo "1️⃣ Registering user..."
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"e2e@test.com","password":"Test123!","name":"E2E Test"}' \
  -s | jq '.'

# 2. Verify (manual step)
echo "2️⃣ Enter verification code:"
read CODE
curl -X POST http://localhost:5000/api/v1/auth/verify \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"e2e@test.com\",\"code\":\"$CODE\"}" \
  -s | jq '.'

# 3. Login
echo "3️⃣ Logging in..."
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"email":"e2e@test.com","password":"Test123!"}' \
  -s | jq '.'

# 4. Upload audio
echo "4️⃣ Uploading audio..."
S3_KEY=$(curl -X POST http://localhost:5000/api/v1/audio/upload \
  -b cookies.txt \
  -F "audio=@sample.mp3" \
  -s | jq -r '.s3_key')
echo "S3 Key: $S3_KEY"

# 5. Start transcription
echo "5️⃣ Starting transcription..."
JOB_ID=$(curl -X POST http://localhost:5000/api/v1/transcribe \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d "{\"s3_key\":\"$S3_KEY\"}" \
  -s | jq -r '.job_id')
echo "Job ID: $JOB_ID"

# 6. Poll for completion
echo "6️⃣ Waiting for transcription..."
while true; do
  STATUS=$(curl -s http://localhost:5000/api/v1/transcribe/status/$JOB_ID \
    -b cookies.txt | jq -r '.status')
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "COMPLETED" ]; then
    break
  fi
  
  sleep 5
done

# 7. Get transcript
echo "7️⃣ Getting transcript..."
TRANSCRIPT=$(curl -s http://localhost:5000/api/v1/transcribe/result/$JOB_ID \
  -b cookies.txt | jq -r '.transcript')
echo "Transcript: $TRANSCRIPT"

# 8. Create prescription
echo "8️⃣ Creating prescription..."
PRESCRIPTION_ID=$(curl -X POST http://localhost:5000/api/v1/prescriptions \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"patient_name":"E2E Test Patient","hospital_id":"hosp_123"}' \
  -s | jq -r '.prescription_id')
echo "Prescription ID: $PRESCRIPTION_ID"

# 9. Transition to InProgress
echo "9️⃣ Transitioning to InProgress..."
curl -X POST http://localhost:5000/api/v1/prescriptions/$PRESCRIPTION_ID/transition-to-in-progress \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d "{\"transcript\":\"$TRANSCRIPT\"}" \
  -s | jq '.'

# 10. Approve all sections
echo "🔟 Approving sections..."
for SECTION in diagnosis medications clinical_notes; do
  curl -X POST http://localhost:5000/api/v1/prescriptions/$PRESCRIPTION_ID/sections/$SECTION/approve \
    -b cookies.txt \
    -s | jq '.'
done

# 11. Finalize
echo "1️⃣1️⃣ Finalizing prescription..."
curl -X POST http://localhost:5000/api/v1/prescriptions/$PRESCRIPTION_ID/finalize \
  -b cookies.txt \
  -s | jq '.'

# 12. Generate PDF
echo "1️⃣2️⃣ Generating PDF..."
PDF_URL=$(curl -X POST http://localhost:5000/api/v1/prescriptions/$PRESCRIPTION_ID/pdf \
  -b cookies.txt \
  -s | jq -r '.pdf_url')
echo "PDF URL: $PDF_URL"

# 13. Download PDF
echo "1️⃣3️⃣ Downloading PDF..."
curl -o prescription.pdf "$PDF_URL"
echo "PDF saved to prescription.pdf"

echo "✅ E2E Test Complete!"
```

---

## 10. Test Data

### Sample Audio Files

Create test audio files with medical content:

```bash
# Using text-to-speech (macOS)
say "Patient name is John Smith, 45 years old. Complains of fever and headache for 3 days. Blood pressure 120 over 80. Diagnosed with viral fever. Prescribed paracetamol 500 milligrams three times daily for 5 days." -o sample.aiff

# Convert to MP3
ffmpeg -i sample.aiff -acodec libmp3lame sample.mp3
```

### Sample Transcripts

```text
Patient name is Rajesh Kumar, 52 years old, male, weighs 75 kilograms.
Patient ID is CGH-1234. Blood pressure is 140 over 90, heart rate 78 beats per minute,
temperature 98.6 Fahrenheit, oxygen saturation 97 percent.

Chief complaint: Persistent cough and chest congestion for 2 weeks.

Diagnosis: Acute bronchitis.

Prescribing Azithromycin tablets, 500 milligrams, once daily for 5 days.
Also prescribe Salbutamol inhaler, 2 puffs, three times daily as needed.
Cetirizine tablets, 10 milligrams, once daily at bedtime for 7 days.

Instructions: Drink warm fluids, avoid cold beverages, rest adequately.
Return if symptoms worsen or fever develops.
```

---

## 11. Continuous Integration

### GitHub Actions Workflow

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: seva_arogya_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/seva_arogya_test
        run: |
          pytest tests/ -v --cov --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 12. Test Checklist

### Pre-Deployment Testing

- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] API endpoints tested
- [ ] Security tests passed
- [ ] Load testing completed
- [ ] E2E workflow tested
- [ ] Health checks passing
- [ ] AWS connectivity verified

### Post-Deployment Testing

- [ ] Health endpoint returns 200
- [ ] AWS connectivity check passes
- [ ] Login flow works
- [ ] Prescription creation works
- [ ] AI extraction works
- [ ] PDF generation works
- [ ] Role-based access enforced
- [ ] CloudWatch logs accessible

---

## 13. Test Reports

### Generate Test Report

```bash
# Run tests with HTML report
pytest tests/ -v --cov --cov-report=html

# Open report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Test Metrics

Track these metrics:
- Test coverage percentage
- Number of tests passing/failing
- Test execution time
- Flaky test rate
- Bug detection rate

---

## 14. Debugging Tests

### Enable Debug Logging

```bash
# Run tests with debug output
pytest tests/ -v -s --log-cli-level=DEBUG

# Run specific test with debugging
pytest tests/test_prescription_service.py::test_create_prescription -v -s --pdb
```

### Common Test Failures

**Database connection fails:**
```bash
# Check PostgreSQL is running
pg_isready

# Check DATABASE_URL
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1;"
```

**AWS service mocks not working:**
```python
# Use moto for AWS mocking
import boto3
from moto import mock_s3, mock_cognito_idp

@mock_s3
@mock_cognito_idp
def test_with_mocks():
    # Your test code
    pass
```

---

## 15. Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Locust Documentation](https://docs.locust.io/)
- [AWS Testing Best Practices](https://aws.amazon.com/blogs/devops/testing-best-practices/)

---

**Testing Guide Version:** 2.0  
**Last Updated:** March 8, 2026
