# Quick Start - AWS Connectivity Testing

## TL;DR

Your deployment now includes automatic AWS connectivity testing. Here's what you need to know:

## Before Every Deployment

The deployment script automatically runs connectivity tests. If they fail, deployment is aborted.

```bash
./deploy_to_aws.sh
```

## Manual Testing Commands

### Test AWS Connectivity (Comprehensive)
```bash
python test_aws_connectivity.py
```
Tests: DNS, HTTP, credentials, boto3 clients, API calls

### Test Cognito Connection (Quick)
```bash
python test_cognito_connection.py
```
Tests: Cognito authentication manager initialization

### Pre-Deployment Check
```bash
bash scripts/pre_deploy_check.sh
```
Runs before deployment to validate local connectivity

### Post-Deployment Validation
```bash
# Get your API URL
cd seva-arogya-infra
API_URL=$(terraform output -raw api_base_url)

# Run validation
bash scripts/validate_deployment.sh "$API_URL"
```
Validates deployed application can connect to AWS services

## Health Check Endpoints

### Basic Health
```bash
curl http://your-alb-url/health
```
Checks: Database, migrations, secrets manager

### AWS Connectivity
```bash
curl http://your-alb-url/health/aws-connectivity
```
Checks: Cognito, S3, Transcribe, Comprehend, Secrets Manager

## Common Issues

### "Cannot connect to endpoint URL"
**Fix**: Run `python test_aws_connectivity.py` for diagnosis

### "Pre-deployment checks failed"
**Fix**: Check internet, firewall, VPN, AWS credentials

### "Post-deployment validation failed"
**Fix**: Check security groups, IAM permissions, VPC NAT gateway

## What Changed

1. **Fixed** - `aws_services/base_client.py` now explicitly passes credentials
2. **Added** - `/health/aws-connectivity` endpoint for monitoring
3. **Added** - Pre-deployment validation in deployment script
4. **Added** - Post-deployment validation after ECS update
5. **Added** - Comprehensive diagnostic tools

## Files to Know

- `test_aws_connectivity.py` - Main diagnostic tool
- `scripts/pre_deploy_check.sh` - Pre-deployment validation
- `scripts/validate_deployment.sh` - Post-deployment validation
- `DEPLOYMENT_TESTING.md` - Full documentation
- `AWS_CONNECTION_FIX.md` - Troubleshooting guide

## Your Original Error - FIXED ✓

**Before**:
```
Could not connect to the endpoint URL: "https://cognito-idp.ap-south-1.amazonaws.com/"
```

**After**:
```
✓ Successfully created cognito-idp client in ap-south-1
✓ Successfully made API call to Cognito
```

The fix ensures credentials from `.env` are explicitly passed to boto3, resolving credential chain issues.

## Next Steps

1. Run `./deploy_to_aws.sh` - It will automatically validate before and after deployment
2. Monitor `/health/aws-connectivity` endpoint for ongoing health checks
3. Set up CloudWatch alarms for the health endpoints

## Need Help?

- **Detailed guide**: See `DEPLOYMENT_TESTING.md`
- **Troubleshooting**: See `AWS_CONNECTION_FIX.md`
- **Summary**: See `AWS_CONNECTIVITY_TESTING_SUMMARY.md`
