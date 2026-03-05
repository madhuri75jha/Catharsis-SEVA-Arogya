# SEVA Arogya Prescription Enhancement - Deployment Guide

## Overview

This guide covers the deployment of the prescription enhancement feature, including database migrations, environment configuration, AWS services setup, and rollout strategy.

## Prerequisites

- AWS account with appropriate permissions
- Database access (RDS PostgreSQL)
- S3 buckets configured (audio, PDF)
- Cognito user pool configured
- CloudWatch Logs access
- Bedrock access (for AI extraction)

## Deployment Steps

### 0. Terraform Infrastructure Updates (If Not Already Done)

**IMPORTANT:** Before deploying the application, ensure Terraform infrastructure is updated with required permissions.

See `TERRAFORM_UPDATES.md` for detailed instructions.

**Quick Summary:**
```bash
cd seva-arogya-infra

# Review changes
terraform plan

# Apply infrastructure updates
terraform apply

# Verify permissions
aws iam list-attached-role-policies --role-name seva-arogya-dev-ecs-task-role
```

**Required Changes:**
- ✅ IAM policy for CloudWatch Logs read access
- ✅ IAM policy for S3 PDF bucket operations
- ✅ IAM policy for S3 cleanup operations
- ✅ Environment variables in ECS task definition
- ✅ S3 PDF bucket (if not exists)
- ✅ CloudWatch Log Group (if not exists)

### 1. Environment Variables Configuration

Update your `.env` file or AWS Secrets Manager with the following new variables:

```bash
# CloudWatch Logs Configuration
CLOUDWATCH_LOG_GROUP_NAME=/aws/ecs/seva-arogya
AWS_CLOUDWATCH_REGION=ap-south-1

# Cleanup Scheduler Configuration
CLEANUP_SCHEDULE_ENABLED=true
CLEANUP_RETENTION_DAYS=30

# PDF Generation Configuration
PDF_GENERATION_TIMEOUT=30
PDF_MAX_FILE_SIZE_MB=10

# Feature Flags
ENABLE_PRESCRIPTION_WORKFLOW=true
ENABLE_CLOUDWATCH_LOGS_VIEWER=true
```

### 2. Database Migrations

#### Step 1: Backup Database

```bash
# Create a backup before running migrations
pg_dump -h <db-host> -U <db-user> -d <db-name> > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Step 2: Run Migrations

```bash
# Execute migration script
python scripts/run_migrations.py
```

This will execute the following migrations in order:
1. `004_add_prescription_state_management.sql` - Adds state, finalized_at, deleted_at columns
2. `005_add_prescription_sections_metadata.sql` - Adds sections, bedrock_payload, metadata columns
3. `006_create_hospitals_table.sql` - Creates hospitals table
4. `007_create_doctors_table.sql` - Creates doctors table
5. `008_create_user_roles_table.sql` - Creates user_roles table for RBAC

#### Step 3: Migrate Existing Prescriptions

```bash
# Migrate existing prescriptions to new schema
python scripts/migrate_existing_prescriptions.py
```

This sets:
- `state` to 'Draft' for all existing prescriptions
- `sections` to empty array
- `created_by_doctor_id` from user_id
- `hospital_id` from user's hospital (if available)

#### Step 4: Seed Hospital Data

```bash
# Seed sample hospital and doctor data
python scripts/seed_hospitals.py
```

### 3. AWS Services Setup

#### Cognito Custom Attributes

Add custom attributes to your Cognito user pool:
- `custom:role` (String) - User role (Doctor, HospitalAdmin, DeveloperAdmin)
- `custom:hospital_id` (String) - Hospital ID for the user

#### CloudWatch Logs

Ensure your ECS task has permissions to read CloudWatch Logs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogStreams",
        "logs:GetLogEvents",
        "logs:FilterLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/ecs/seva-arogya:*"
    }
  ]
}
```

#### S3 Permissions

Ensure your ECS task has permissions for PDF generation:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::your-pdf-bucket/*"
    }
  ]
}
```

#### Bedrock Permissions

Ensure your ECS task has permissions for Bedrock:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:*:*:model/anthropic.claude-3-haiku-20240307-v1:0"
    }
  ]
}
```

### 4. Application Deployment

#### Option A: Docker Deployment

```bash
# Build Docker image
docker build -t seva-arogya:latest .

# Tag for ECR
docker tag seva-arogya:latest <account-id>.dkr.ecr.<region>.amazonaws.com/seva-arogya:latest

# Push to ECR
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/seva-arogya:latest

# Update ECS service
aws ecs update-service --cluster seva-arogya --service seva-arogya-service --force-new-deployment
```

#### Option B: Direct Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python app.py
```

### 5. Verification

#### Check Database Migrations

```sql
-- Verify migrations table
SELECT * FROM schema_migrations ORDER BY executed_at DESC;

-- Verify prescription states
SELECT state, COUNT(*) FROM prescriptions GROUP BY state;

-- Verify hospitals table
SELECT COUNT(*) FROM hospitals;

-- Verify user_roles table
SELECT role, COUNT(*) FROM user_roles GROUP BY role;
```

#### Check Application Health

```bash
# Health check
curl http://localhost:5000/health

# AWS connectivity check
curl http://localhost:5000/health/aws-connectivity
```

#### Test Prescription Workflow

1. Login as a doctor
2. Create a new prescription (should be in Draft state)
3. Transition to InProgress (should populate sections from Bedrock)
4. Approve/reject sections
5. Finalize prescription
6. Generate PDF
7. Test soft delete and restore

### 6. Rollout Strategy

#### Phase 1: Staging Environment (Week 1)

1. Deploy to staging environment
2. Run all migrations
3. Test complete workflow with sample data
4. Verify all API endpoints
5. Test frontend pages
6. Verify role-based access control
7. Test PDF generation
8. Test cleanup scheduler

#### Phase 2: Production Deployment (Week 2)

1. Schedule maintenance window (low traffic period)
2. Create database backup
3. Deploy application with feature flags disabled
4. Run database migrations
5. Migrate existing prescriptions
6. Seed hospital data
7. Enable feature flags gradually:
   - `ENABLE_PRESCRIPTION_WORKFLOW=true`
   - `ENABLE_CLOUDWATCH_LOGS_VIEWER=true` (DeveloperAdmin only)
8. Monitor logs and metrics
9. Verify no errors in CloudWatch

#### Phase 3: Gradual Rollout (Week 3-4)

1. Enable for pilot users (selected doctors)
2. Gather feedback
3. Monitor performance metrics
4. Fix any issues
5. Enable for all users

### 7. Rollback Procedures

#### If Issues Detected During Deployment

1. Disable feature flags:
   ```bash
   ENABLE_PRESCRIPTION_WORKFLOW=false
   ENABLE_CLOUDWATCH_LOGS_VIEWER=false
   ```

2. Revert to previous application version:
   ```bash
   aws ecs update-service --cluster seva-arogya --service seva-arogya-service --task-definition seva-arogya:<previous-version>
   ```

3. If database issues, restore from backup:
   ```bash
   psql -h <db-host> -U <db-user> -d <db-name> < backup_<timestamp>.sql
   ```

#### Rollback Checklist

- [ ] Disable feature flags
- [ ] Revert application deployment
- [ ] Restore database from backup (if needed)
- [ ] Verify application health
- [ ] Notify users of rollback
- [ ] Document issues for investigation

### 8. Monitoring and Alerts

#### Key Metrics to Monitor

1. **Prescription Creation Rate**
   - Metric: `prescriptions_created_per_hour`
   - Alert: Drop > 50% from baseline

2. **PDF Generation Success Rate**
   - Metric: `pdf_generation_success_rate`
   - Alert: < 95%

3. **State Transition Errors**
   - Metric: `state_transition_errors_per_hour`
   - Alert: > 10 errors/hour

4. **Cleanup Scheduler Execution**
   - Metric: `cleanup_scheduler_runs`
   - Alert: No execution in 25 hours

5. **API Response Times**
   - Metric: `api_response_time_p95`
   - Alert: > 2 seconds

#### CloudWatch Alarms

```bash
# Create alarm for prescription creation errors
aws cloudwatch put-metric-alarm \
  --alarm-name seva-arogya-prescription-errors \
  --alarm-description "Alert on prescription creation errors" \
  --metric-name PrescriptionErrors \
  --namespace SEVA/Arogya \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

### 9. Post-Deployment Tasks

- [ ] Verify all migrations executed successfully
- [ ] Test prescription workflow end-to-end
- [ ] Verify role-based access control
- [ ] Test PDF generation
- [ ] Verify cleanup scheduler is running
- [ ] Check CloudWatch logs viewer (DeveloperAdmin)
- [ ] Monitor error rates
- [ ] Gather user feedback
- [ ] Update documentation with any issues/learnings

### 10. Troubleshooting

#### Issue: Migrations Fail

**Solution:**
1. Check database connectivity
2. Verify user has CREATE TABLE permissions
3. Check migration logs: `SELECT * FROM schema_migrations WHERE success = FALSE`
4. Manually fix issues and re-run migrations

#### Issue: PDF Generation Fails

**Solution:**
1. Check S3 bucket permissions
2. Verify `PDF_GENERATION_TIMEOUT` is sufficient
3. Check hospital logo URLs are accessible
4. Review CloudWatch logs for errors

#### Issue: Cleanup Scheduler Not Running

**Solution:**
1. Verify `CLEANUP_SCHEDULE_ENABLED=true`
2. Check APScheduler logs
3. Verify database connectivity
4. Check S3 delete permissions

#### Issue: Role Sync Fails

**Solution:**
1. Verify Cognito custom attributes exist
2. Check user_roles table exists
3. Verify database permissions
4. Check login logs for errors

## Support

For issues or questions:
- Check CloudWatch logs: `/aws/ecs/seva-arogya`
- Review application logs: `logs/app.log`
- Contact: DevOps team

## References

- [Integration Guide](INTEGRATION_GUIDE.md)
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md)
- [Requirements Document](.kiro/specs/seva-arogya-prescription-enhancement/requirements.md)
- [Design Document](.kiro/specs/seva-arogya-prescription-enhancement/design.md)
