# SEVA Arogya - Complete Deployment Guide

**Version:** 2.0  
**Last Updated:** March 8, 2026  
**Status:** Production Ready

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Setup](#aws-setup)
3. [Infrastructure Deployment](#infrastructure-deployment)
4. [Application Deployment](#application-deployment)
5. [Database Setup](#database-setup)
6. [Validation](#validation)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)

---

## 1. Prerequisites

### Required Tools

- **Terraform** >= 1.6 ([Install](https://www.terraform.io/downloads))
- **AWS CLI** configured ([Install](https://aws.amazon.com/cli/))
- **Docker** ([Install](https://docs.docker.com/get-docker/))
- **Python** 3.11+
- **PostgreSQL** client tools

### AWS Account Requirements

- AWS account with appropriate permissions
- IAM user with admin access (or specific permissions)
- AWS CLI configured with credentials

```bash
# Configure AWS CLI
aws configure
# Enter: Access Key ID, Secret Access Key, Region (ap-south-1), Output format (json)

# Verify configuration
aws sts get-caller-identity
```

### Required AWS Permissions

Your IAM user/role needs permissions for:
- VPC, Subnets, Security Groups
- ECS, ECR, ALB
- RDS, S3, Secrets Manager
- Cognito, IAM
- CloudWatch, Lambda
- Transcribe, Comprehend Medical, Bedrock, Translate

---

## 2. AWS Setup

### Step 1: Create Cognito User Pool

```bash
# Create User Pool
aws cognito-idp create-user-pool \
  --pool-name seva-arogya-users \
  --policies "PasswordPolicy={MinimumLength=8,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true}" \
  --auto-verified-attributes email \
  --region ap-south-1

# Note the UserPoolId from output

# Create App Client
aws cognito-idp create-user-pool-client \
  --user-pool-id <YOUR_USER_POOL_ID> \
  --client-name seva-arogya-client \
  --explicit-auth-flows USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --region ap-south-1

# Note the ClientId from output
```

### Step 2: Create S3 Buckets

```bash
# Generate unique ID
UNIQUE_ID=$(date +%s)

# Audio bucket
aws s3 mb s3://seva-arogya-audio-${UNIQUE_ID} --region ap-south-1

# PDF bucket
aws s3 mb s3://seva-arogya-pdf-${UNIQUE_ID} --region ap-south-1

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket seva-arogya-audio-${UNIQUE_ID} \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

aws s3api put-bucket-encryption \
  --bucket seva-arogya-pdf-${UNIQUE_ID} \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Block public access
aws s3api put-public-access-block \
  --bucket seva-arogya-audio-${UNIQUE_ID} \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

aws s3api put-public-access-block \
  --bucket seva-arogya-pdf-${UNIQUE_ID} \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

### Step 3: Create Secrets in Secrets Manager

```bash
# Database credentials
aws secretsmanager create-secret \
  --name seva-arogya/db-credentials \
  --secret-string '{"host":"<rds-endpoint>","port":5432,"database":"seva_arogya","username":"sevaadmin","password":"<secure-password>"}' \
  --region ap-south-1

# Flask secret key
aws secretsmanager create-secret \
  --name seva-arogya/flask-secret \
  --secret-string "$(openssl rand -base64 32)" \
  --region ap-south-1

# JWT secret
aws secretsmanager create-secret \
  --name seva-arogya/jwt-secret \
  --secret-string "$(openssl rand -base64 32)" \
  --region ap-south-1
```

### Step 4: Enable Bedrock Access

```bash
# Request Bedrock model access (one-time)
# Go to AWS Console → Bedrock → Model access
# Request access to: Claude 3 Sonnet

# Or use CLI (if available in your region)
aws bedrock list-foundation-models --region us-east-1
```

---

## 3. Infrastructure Deployment

### Step 1: Configure Environment

```bash
cd seva-arogya-infra

# Copy environment template
cp ../.env.example ../.env

# Edit .env with your values
nano ../.env
```

**Required variables:**
```bash
# AWS Configuration
AWS_REGION=ap-south-1
PROJECT_NAME=seva-arogya
ENV_NAME=dev

# Container Image (update after ECR push)
CONTAINER_IMAGE=<account-id>.dkr.ecr.ap-south-1.amazonaws.com/seva-arogya-dev-backend:latest

# Database
DB_NAME=seva_arogya
DB_USERNAME=sevaadmin
DB_PASSWORD=<secure-password>

# Application Secrets
FLASK_SECRET_KEY=<32-char-random>
JWT_SECRET=<32-char-random>

# Cognito (from Step 1)
AWS_COGNITO_USER_POOL_ID=<pool-id>
AWS_COGNITO_CLIENT_ID=<client-id>

# S3 Buckets (from Step 2)
S3_AUDIO_BUCKET=seva-arogya-audio-<unique-id>
S3_PDF_BUCKET=seva-arogya-pdf-<unique-id>

# Bedrock
BEDROCK_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Features
ENABLE_HTTPS=false
ENABLE_PRESCRIPTION_PDF_LAMBDA=true
```

### Step 2: Initialize Terraform

```bash
terraform init
```

### Step 3: Plan Infrastructure

```bash
terraform plan -out=tfplan
```

Review the plan carefully. Expected resources:
- VPC with public/private subnets (2 AZs)
- ALB with target group
- ECS cluster and service
- RDS PostgreSQL instance
- Security groups
- IAM roles and policies
- Lambda function (PDF generator)
- CloudWatch log groups

### Step 4: Apply Infrastructure

```bash
terraform apply tfplan
```

**Deployment time:** 10-15 minutes

**Note outputs:**
```bash
terraform output
```

Save these values:
- `alb_dns_name` - Application URL
- `ecr_repository_url` - For Docker push
- `rds_endpoint` - Database endpoint

---

## 4. Application Deployment

### Step 1: Build Docker Image

```bash
# Return to project root
cd ..

# Build image
docker build -t seva-arogya-backend:latest .
```

### Step 2: Push to ECR

```bash
# Get ECR URL from Terraform output
ECR_URL=$(cd seva-arogya-infra && terraform output -raw ecr_repository_url)

# Authenticate Docker to ECR
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin $ECR_URL

# Tag image
docker tag seva-arogya-backend:latest $ECR_URL:latest

# Push to ECR
docker push $ECR_URL:latest
```

### Step 3: Update ECS Service

```bash
# Force new deployment
aws ecs update-service \
  --cluster seva-arogya-dev-cluster \
  --service seva-arogya-dev-api \
  --force-new-deployment \
  --region ap-south-1

# Wait for deployment to stabilize (2-3 minutes)
aws ecs wait services-stable \
  --cluster seva-arogya-dev-cluster \
  --services seva-arogya-dev-api \
  --region ap-south-1
```

### Step 4: Verify Deployment

```bash
# Get ALB URL
ALB_URL=$(cd seva-arogya-infra && terraform output -raw alb_dns_name)

# Health check
curl http://$ALB_URL/health

# AWS connectivity check
curl http://$ALB_URL/health/aws-connectivity
```

---

## 5. Database Setup

### Step 1: Update Secrets Manager

Update the database endpoint in Secrets Manager:

```bash
# Get RDS endpoint
RDS_ENDPOINT=$(cd seva-arogya-infra && terraform output -raw rds_endpoint)

# Update secret
aws secretsmanager update-secret \
  --secret-id seva-arogya/db-credentials \
  --secret-string "{\"host\":\"$RDS_ENDPOINT\",\"port\":5432,\"database\":\"seva_arogya\",\"username\":\"sevaadmin\",\"password\":\"<your-password>\"}" \
  --region ap-south-1
```

### Step 2: Run Migrations

Migrations run automatically on app startup. To run manually:

```bash
python migrations/run_migration.py
```

Migrations executed:
1. `001_add_streaming_columns.sql` - Streaming transcription support
2. `002_add_consultation_tables.sql` - Consultation management
3. `003_add_bedrock_columns.sql` - Bedrock integration
4. `004_add_prescription_state_management.sql` - State machine
5. `005_add_prescription_sections_metadata.sql` - Section approval
6. `006_create_hospitals_table.sql` - Hospital management
7. `007_create_doctors_table.sql` - Doctor profiles
8. `008_create_user_roles_table.sql` - RBAC

### Step 3: Seed Initial Data

```bash
python scripts/seed_hospitals.py
```

This creates:
- 2 sample hospitals
- 3 sample doctors
- 5 user roles

---

## 6. Validation

### Pre-Deployment Validation

```bash
# Run pre-deployment checks
bash scripts/pre_deploy_check.sh
```

Validates:
- DNS resolution for AWS endpoints
- HTTP connectivity
- AWS credentials
- Boto3 client creation

### Post-Deployment Validation

```bash
# Get ALB URL
ALB_URL=$(cd seva-arogya-infra && terraform output -raw alb_dns_name)

# Run validation script
bash scripts/validate_deployment.sh http://$ALB_URL
```

Validates:
- Basic health check
- AWS connectivity (Cognito, S3, Transcribe, Comprehend, Secrets Manager)
- Response times
- Error handling

### Manual Testing Checklist

- [ ] Login with test user
- [ ] Create prescription (Draft)
- [ ] Upload audio and transcribe
- [ ] Transition to InProgress (AI extraction)
- [ ] Approve/reject sections
- [ ] Finalize prescription
- [ ] Generate and download PDF
- [ ] Test soft delete and restore
- [ ] Verify role-based access
- [ ] Check CloudWatch logs viewer

---

## 7. Rollback Procedures

### Application Rollback

```bash
# Revert to previous task definition
aws ecs update-service \
  --cluster seva-arogya-dev-cluster \
  --service seva-arogya-dev-api \
  --task-definition seva-arogya-dev:<previous-revision> \
  --region ap-south-1
```

### Database Rollback

```bash
# Restore from backup
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier seva-arogya-dev-db \
  --target-db-instance-identifier seva-arogya-dev-db-restored \
  --restore-time 2026-03-08T10:00:00Z \
  --region ap-south-1

# Or restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier seva-arogya-dev-db-restored \
  --db-snapshot-identifier seva-arogya-dev-db-snapshot-20260308 \
  --region ap-south-1
```

### Infrastructure Rollback

```bash
cd seva-arogya-infra

# Revert specific resource
terraform apply -target=<resource> -destroy

# Or full rollback
terraform destroy
```

### Feature Flag Rollback

Disable features without redeployment:

```bash
# Update environment variables in ECS task definition
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json \
  --region ap-south-1

# Update with ENABLE_PRESCRIPTION_WORKFLOW=false
```

---

## 8. Troubleshooting

### ECS Tasks Not Starting

```bash
# Check service events
aws ecs describe-services \
  --cluster seva-arogya-dev-cluster \
  --services seva-arogya-dev-api \
  --region ap-south-1 \
  --query 'services[0].events[0:5]'

# Check task status
aws ecs list-tasks \
  --cluster seva-arogya-dev-cluster \
  --service-name seva-arogya-dev-api \
  --region ap-south-1

# View logs
aws logs tail /ecs/seva-arogya-dev --follow --region ap-south-1
```

**Common causes:**
- Image pull failures (check ECR permissions)
- Insufficient memory/CPU
- Health check failures
- Security group misconfiguration

### ALB Health Checks Failing

```bash
# Check target health
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn> \
  --region ap-south-1
```

**Common causes:**
- Application not listening on correct port (5000)
- `/health` endpoint not responding
- Security group not allowing ALB → ECS traffic
- Application startup failures

### Database Connection Issues

```bash
# Test connection from local machine
psql -h <rds-endpoint> -U sevaadmin -d seva_arogya

# Check security group
aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=*rds*" \
  --region ap-south-1 \
  --query 'SecurityGroups[0].IpPermissions'
```

**Common causes:**
- Security group not allowing ECS → RDS traffic
- Incorrect credentials in Secrets Manager
- Database not created
- RDS instance not available

### Secrets Manager Access Issues

```bash
# Test secret retrieval
aws secretsmanager get-secret-value \
  --secret-id seva-arogya/db-credentials \
  --region ap-south-1

# Check IAM permissions
aws iam get-role-policy \
  --role-name seva-arogya-dev-ecs-task-role \
  --policy-name secrets-manager \
  --region ap-south-1
```

### Bedrock Access Issues

```bash
# Check model access
aws bedrock list-foundation-models --region us-east-1

# Test model invocation
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-3-sonnet-20240229-v1:0 \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":100,"messages":[{"role":"user","content":"Hello"}]}' \
  --region us-east-1 \
  output.json
```

**Common causes:**
- Model access not requested in Bedrock console
- IAM permissions missing
- Wrong region (Bedrock not available in all regions)

---

## 9. Automated Deployment

### One-Command Deployment

```bash
./deploy_to_aws.sh
```

This script:
1. Runs pre-deployment checks
2. Packages Lambda function
3. Deploys infrastructure with Terraform
4. Builds and pushes Docker image
5. Updates ECS service
6. Runs post-deployment validation

### Deployment Environments

| Environment | Purpose | Configuration |
|-------------|---------|---------------|
| **Development** | Local testing | 1 ECS task, small RDS |
| **Staging** | Pre-production | 2 ECS tasks, medium RDS |
| **Production** | Live system | 2-10 ECS tasks (auto-scale), Multi-AZ RDS |

---

## 10. Monitoring Setup

### CloudWatch Alarms

```bash
# CPU utilization alarm
aws cloudwatch put-metric-alarm \
  --alarm-name seva-arogya-high-cpu \
  --alarm-description "Alert when CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --region ap-south-1

# Error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name seva-arogya-high-errors \
  --alarm-description "Alert when error rate > 5%" \
  --metric-name Errors \
  --namespace SEVA/Arogya \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --region ap-south-1
```

### Log Monitoring

```bash
# View application logs
aws logs tail /ecs/seva-arogya-dev --follow --region ap-south-1

# Filter for errors
aws logs filter-log-events \
  --log-group-name /ecs/seva-arogya-dev \
  --filter-pattern "ERROR" \
  --region ap-south-1

# Query with Insights
aws logs start-query \
  --log-group-name /ecs/seva-arogya-dev \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20' \
  --region ap-south-1
```

---

## 11. Cost Optimization

### Development Environment

```bash
# Stop RDS when not in use
aws rds stop-db-instance \
  --db-instance-identifier seva-arogya-dev-db \
  --region ap-south-1

# Scale ECS to 0 tasks
aws ecs update-service \
  --cluster seva-arogya-dev-cluster \
  --service seva-arogya-dev-api \
  --desired-count 0 \
  --region ap-south-1

# Start RDS
aws rds start-db-instance \
  --db-instance-identifier seva-arogya-dev-db \
  --region ap-south-1

# Scale ECS back up
aws ecs update-service \
  --cluster seva-arogya-dev-cluster \
  --service seva-arogya-dev-api \
  --desired-count 1 \
  --region ap-south-1
```

### Cost Monitoring

```bash
# Get cost and usage
aws ce get-cost-and-usage \
  --time-period Start=2026-03-01,End=2026-03-08 \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

---

## 12. Security Hardening

### Enable HTTPS

1. Request ACM certificate:
```bash
aws acm request-certificate \
  --domain-name sevaarogya.in \
  --validation-method DNS \
  --region ap-south-1
```

2. Update `.env`:
```bash
ENABLE_HTTPS=true
CERTIFICATE_ARN=arn:aws:acm:ap-south-1:...:certificate/...
```

3. Apply Terraform:
```bash
cd seva-arogya-infra
terraform apply
```

### Enable WAF (Optional)

```bash
# Create WAF web ACL
aws wafv2 create-web-acl \
  --name seva-arogya-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules file://waf-rules.json \
  --region ap-south-1

# Associate with ALB
aws wafv2 associate-web-acl \
  --web-acl-arn <waf-arn> \
  --resource-arn <alb-arn> \
  --region ap-south-1
```

---

## 13. Backup & Disaster Recovery

### Database Backups

```bash
# Create manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier seva-arogya-dev-db \
  --db-snapshot-identifier seva-arogya-manual-$(date +%Y%m%d) \
  --region ap-south-1

# List snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier seva-arogya-dev-db \
  --region ap-south-1
```

### S3 Versioning

```bash
# Enable versioning on PDF bucket
aws s3api put-bucket-versioning \
  --bucket seva-arogya-pdf-<unique-id> \
  --versioning-configuration Status=Enabled \
  --region ap-south-1
```

---

## 14. CI/CD Setup (Optional)

### GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-south-1
      
      - name: Login to ECR
        run: |
          aws ecr get-login-password --region ap-south-1 | \
          docker login --username AWS --password-stdin ${{ secrets.ECR_URL }}
      
      - name: Build and push Docker image
        run: |
          docker build -t seva-arogya:latest .
          docker tag seva-arogya:latest ${{ secrets.ECR_URL }}:latest
          docker push ${{ secrets.ECR_URL }}:latest
      
      - name: Update ECS service
        run: |
          aws ecs update-service \
            --cluster seva-arogya-dev-cluster \
            --service seva-arogya-dev-api \
            --force-new-deployment \
            --region ap-south-1
```

---

## 15. Production Deployment Checklist

### Pre-Deployment
- [ ] Backup database
- [ ] Review Terraform plan
- [ ] Test in staging environment
- [ ] Update environment variables
- [ ] Verify IAM permissions
- [ ] Check AWS service quotas

### Deployment
- [ ] Deploy infrastructure (Terraform)
- [ ] Build and push Docker image
- [ ] Update ECS service
- [ ] Run database migrations
- [ ] Seed initial data
- [ ] Verify health checks

### Post-Deployment
- [ ] Run validation scripts
- [ ] Test critical workflows
- [ ] Monitor CloudWatch logs
- [ ] Check error rates
- [ ] Verify performance metrics
- [ ] Update documentation

### Rollback Plan
- [ ] Previous task definition ARN noted
- [ ] Database backup confirmed
- [ ] Rollback procedure tested
- [ ] Team notified of deployment

---

## 16. Maintenance

### Regular Tasks

**Daily:**
- Monitor CloudWatch alarms
- Check error rates
- Review application logs

**Weekly:**
- Review cost and usage
- Check database performance
- Update security patches

**Monthly:**
- Review and rotate secrets
- Analyze usage patterns
- Optimize resource allocation
- Update dependencies

### Updates

```bash
# Update application
docker build -t seva-arogya:latest .
docker push $ECR_URL:latest
aws ecs update-service --cluster seva-arogya-dev-cluster --service seva-arogya-dev-api --force-new-deployment

# Update infrastructure
cd seva-arogya-infra
terraform plan
terraform apply
```

---

## 17. Support

### Diagnostic Commands

```bash
# Check ECS tasks
aws ecs list-tasks --cluster seva-arogya-dev-cluster --region ap-south-1

# Describe task
aws ecs describe-tasks \
  --cluster seva-arogya-dev-cluster \
  --tasks <task-arn> \
  --region ap-south-1

# View logs
aws logs tail /ecs/seva-arogya-dev --follow --region ap-south-1

# Check RDS status
aws rds describe-db-instances \
  --db-instance-identifier seva-arogya-dev-db \
  --region ap-south-1 \
  --query 'DBInstances[0].DBInstanceStatus'
```

### Getting Help

1. Check CloudWatch logs: `/ecs/seva-arogya-dev`
2. Review ECS service events
3. Verify security group rules
4. Check IAM role permissions
5. Run diagnostic scripts

---

## 18. References

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [AWS Transcribe Medical](https://docs.aws.amazon.com/transcribe/latest/dg/transcribe-medical.html)
- [AWS Comprehend Medical](https://docs.aws.amazon.com/comprehend-medical/)

---

**Deployment Guide Version:** 2.0  
**Last Updated:** March 8, 2026  
**Next Review:** April 8, 2026
