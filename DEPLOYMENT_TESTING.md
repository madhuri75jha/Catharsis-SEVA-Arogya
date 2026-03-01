# Deployment Testing & Validation

This document describes the automated testing and validation that runs during deployment to ensure AWS connectivity and service health.

## Overview

The deployment process now includes three stages of testing:

1. **Pre-Deployment Checks** - Validates local AWS connectivity before deploying
2. **Deployment** - Deploys infrastructure and application
3. **Post-Deployment Validation** - Validates deployed application can connect to AWS services

## Testing Stages

### 1. Pre-Deployment Checks

**When**: Before any deployment starts  
**Purpose**: Catch connectivity issues early, before wasting time on deployment  
**Script**: `scripts/pre_deploy_check.sh`

Tests performed:
- DNS resolution for AWS endpoints
- HTTP connectivity to AWS services
- AWS credentials validation
- Boto3 client creation
- Proxy settings check

**How to run manually**:
```bash
bash scripts/pre_deploy_check.sh
```

**What it checks**:
```bash
✓ cognito-idp.ap-south-1.amazonaws.com resolves to IP
✓ s3.ap-south-1.amazonaws.com resolves to IP
✓ Can connect to Cognito endpoint
✓ AWS credentials are set
✓ Successfully created cognito-idp client
✓ Successfully made API call to Cognito
```

**If it fails**:
- Deployment is aborted
- Error messages indicate the specific issue
- Fix the issue and retry

### 2. Deployment

**When**: After pre-deployment checks pass  
**Purpose**: Deploy infrastructure and application to AWS  
**Script**: `deploy_to_aws.sh`

Steps:
1. Run pre-deployment checks
2. Terraform init/plan/apply
3. Docker build/push to ECR
4. Update ECS service
5. Run post-deployment validation

### 3. Post-Deployment Validation

**When**: After deployment completes  
**Purpose**: Verify deployed application can connect to all AWS services  
**Script**: `scripts/validate_deployment.sh`

Tests performed:
- Basic health check (`/health`)
- AWS connectivity check (`/health/aws-connectivity`)
  - Cognito connectivity
  - S3 Audio bucket connectivity
  - S3 PDF bucket connectivity
  - Transcribe connectivity
  - Comprehend Medical connectivity
  - Secrets Manager connectivity

**How to run manually**:
```bash
# Get your API URL from Terraform
cd seva-arogya-infra
API_URL=$(terraform output -raw api_base_url)

# Run validation
bash scripts/validate_deployment.sh "$API_URL"
```

**What it checks**:
```bash
==> Step 1: Basic Health Check
  ✓ Basic Health is healthy (HTTP 200)

==> Step 2: AWS Connectivity Check
  ✓ AWS Connectivity is healthy (HTTP 200)
  
✓ Deployment Validation Successful
```

**If it fails**:
- Detailed error messages show which service failed
- Common causes and fixes are displayed
- Deployment is marked as failed

## API Endpoints

### `/health`

Basic health check endpoint that validates:
- Database connectivity
- Database migrations status
- Secrets Manager connectivity

**Example**:
```bash
curl http://your-alb-url/health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": 1234567890.123,
  "checks": {
    "database": "healthy",
    "migrations": {
      "status": "up_to_date",
      "applied": 5,
      "pending": 0
    },
    "secrets_manager": "healthy"
  }
}
```

### `/health/aws-connectivity`

AWS connectivity check endpoint that validates:
- Cognito User Pool access
- S3 bucket access (audio and PDF)
- Transcribe service access
- Comprehend Medical service access
- Secrets Manager access

**Example**:
```bash
curl http://your-alb-url/health/aws-connectivity
```

**Timeout tuning**:
If the ALB returns HTTP 504 (timeout), reduce per-check timeout:
```
AWS_CONNECTIVITY_CHECK_TIMEOUT=5
```
This keeps the endpoint under typical ALB idle timeouts while still validating connectivity.

**Response**:
```json
{
  "overall_status": "healthy",
  "timestamp": 1234567890.123,
  "region": "ap-south-1",
  "checks": {
    "cognito": {
      "status": "healthy",
      "service": "cognito-idp",
      "endpoint": "cognito-idp.ap-south-1.amazonaws.com",
      "duration_ms": 123.45,
      "user_pool_name": "seva-arogya-dev-users",
      "message": "Successfully connected to Cognito"
    },
    "s3_audio": {
      "status": "healthy",
      "service": "s3",
      "endpoint": "s3.ap-south-1.amazonaws.com",
      "duration_ms": 89.12,
      "bucket": "seva-arogya-dev-audio-123456789",
      "message": "Successfully connected to S3"
    },
    "s3_pdf": {
      "status": "healthy",
      "service": "s3",
      "duration_ms": 76.34,
      "message": "Successfully connected to S3"
    },
    "transcribe": {
      "status": "healthy",
      "service": "transcribe",
      "duration_ms": 234.56,
      "message": "Successfully connected to Transcribe"
    },
    "comprehend": {
      "status": "healthy",
      "service": "comprehendmedical",
      "duration_ms": 345.67,
      "message": "Successfully connected to Comprehend Medical"
    },
    "secrets_manager": {
      "status": "healthy",
      "service": "secretsmanager",
      "duration_ms": 98.76,
      "message": "Successfully connected to Secrets Manager"
    }
  }
}
```

## CI/CD Integration

### GitHub Actions

The deployment workflow (`.github/workflows/deploy.yml`) includes all three testing stages:

**Jobs**:
1. `pre-deployment-checks` - Runs connectivity tests
2. `deploy` - Deploys to AWS
3. `post-deployment-validation` - Validates deployment

**Required Secrets**:
```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_COGNITO_USER_POOL_ID
AWS_COGNITO_CLIENT_ID
S3_AUDIO_BUCKET
S3_PDF_BUCKET
DB_SECRET_NAME
PROJECT_NAME
ENV_NAME
DB_NAME
DB_USERNAME
DB_PASSWORD
FLASK_SECRET_KEY
JWT_SECRET
CORS_ALLOWED_ORIGINS
CONTAINER_IMAGE
ENABLE_HTTPS
```

**Workflow Triggers**:
- Push to `main` or `develop` branches
- Manual trigger via GitHub Actions UI

### Local Development

Run tests locally before pushing:

```bash
# Pre-deployment checks
bash scripts/pre_deploy_check.sh

# Full deployment with validation
./deploy_to_aws.sh

# Post-deployment validation only
bash scripts/validate_deployment.sh http://your-alb-url
```

## Troubleshooting

### Pre-Deployment Checks Fail

**DNS Resolution Failed**:
```
✗ cognito-idp.ap-south-1.amazonaws.com - DNS resolution failed
```
- Check internet connection
- Check DNS settings
- Try: `nslookup cognito-idp.ap-south-1.amazonaws.com`

**HTTP Connectivity Failed**:
```
✗ Cannot connect to Cognito endpoint
```
- Check firewall settings
- Disable VPN temporarily
- Check proxy settings

**AWS Credentials Invalid**:
```
✗ AWS_ACCESS_KEY_ID: Not set
```
- Verify `.env` file has correct credentials
- Check credentials are active in AWS IAM

**Boto3 Client Creation Failed**:
```
✗ Failed to create client: Could not connect to endpoint
```
- Check all of the above
- Try: `aws cognito-idp list-user-pools --max-results 1 --region ap-south-1`

### Post-Deployment Validation Fails

**Basic Health Check Failed**:
```
✗ Basic Health check failed (HTTP 503)
```
- Check ECS task logs
- Verify database connectivity
- Check Secrets Manager access

**AWS Connectivity Check Failed**:
```
✗ AWS Connectivity check failed
```
- Check security group rules (must allow outbound HTTPS)
- Verify IAM task role has required permissions
- Check VPC has NAT gateway for private subnets
- Verify AWS resources exist (Cognito pool, S3 buckets, etc.)

**Specific Service Failed**:
```json
{
  "cognito": {
    "status": "unhealthy",
    "error": "connection_failed",
    "message": "Cannot connect to Cognito endpoint"
  }
}
```
- Check security group allows outbound to AWS services
- Verify VPC endpoints if using private subnets
- Check IAM permissions for that specific service

## Files Added/Modified

### New Files
- `aws_services/connectivity_checker.py` - AWS connectivity checker class
- `scripts/pre_deploy_check.sh` - Pre-deployment validation script
- `scripts/validate_deployment.sh` - Post-deployment validation script
- `.github/workflows/deploy.yml` - GitHub Actions CI/CD workflow
- `DEPLOYMENT_TESTING.md` - This documentation

### Modified Files
- `app.py` - Added `/health/aws-connectivity` endpoint
- `deploy_to_aws.sh` - Integrated pre and post deployment checks
- `aws_services/base_client.py` - Improved credential handling and error logging

## Best Practices

1. **Always run pre-deployment checks** before deploying to catch issues early
2. **Monitor post-deployment validation** to ensure deployment succeeded
3. **Check CloudWatch logs** if validation fails for detailed error messages
4. **Use the health endpoints** for monitoring and alerting
5. **Run validation after infrastructure changes** to verify connectivity

## Monitoring

Set up CloudWatch alarms for the health endpoints:

```bash
# Create alarm for health endpoint
aws cloudwatch put-metric-alarm \
  --alarm-name seva-arogya-health-check \
  --alarm-description "Alert when health check fails" \
  --metric-name HealthCheckStatus \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 1 \
  --comparison-operator LessThanThreshold
```

## Support

If you encounter issues:

1. Check this documentation
2. Review CloudWatch logs
3. Run diagnostic scripts manually
4. Check AWS service status: https://status.aws.amazon.com/
