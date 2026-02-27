# Deployment Checklist - SEVA Arogya AWS Integration

Use this checklist to ensure all steps are completed before deploying to production.

## Pre-Deployment

### 1. AWS Infrastructure Setup

- [ ] **Terraform Infrastructure Deployed**
  - [ ] VPC and networking configured
  - [ ] RDS PostgreSQL instance created
  - [ ] S3 buckets created (audio and PDF)
  - [ ] Cognito User Pool created
  - [ ] Cognito App Client created
  - [ ] IAM roles and policies configured
  - [ ] Security groups configured
  - [ ] CloudWatch log groups created

- [ ] **Cognito Configuration**
  - [ ] User Pool ID obtained
  - [ ] App Client ID obtained
  - [ ] App Client Secret obtained (if using)
  - [ ] Password policy configured
  - [ ] Email verification enabled
  - [ ] MFA settings configured (optional)

- [ ] **S3 Buckets Configuration**
  - [ ] Audio bucket created with unique name
  - [ ] PDF bucket created with unique name
  - [ ] Server-side encryption enabled (AES256)
  - [ ] Bucket policies configured
  - [ ] CORS configuration set (if needed)
  - [ ] Lifecycle policies configured (optional)

- [ ] **RDS Database Setup**
  - [ ] PostgreSQL instance running
  - [ ] Database `seva_arogya` created
  - [ ] Master credentials secured
  - [ ] Security group allows connections
  - [ ] Backup retention configured
  - [ ] Encryption at rest enabled

- [ ] **Secrets Manager**
  - [ ] Database credentials secret created (`seva-arogya/db-credentials`)
  - [ ] Flask secret key created (`seva-arogya/flask-secret`)
  - [ ] JWT secret created (`seva-arogya/jwt-secret`)
  - [ ] Secrets rotation configured (optional)

### 2. IAM Permissions

- [ ] **ECS Task Role Created** with permissions for:
  - [ ] cognito-idp:InitiateAuth
  - [ ] cognito-idp:SignUp
  - [ ] cognito-idp:ConfirmSignUp
  - [ ] cognito-idp:GetUser
  - [ ] cognito-idp:GlobalSignOut
  - [ ] transcribe:StartMedicalTranscriptionJob
  - [ ] transcribe:GetMedicalTranscriptionJob
  - [ ] comprehendmedical:DetectEntitiesV2
  - [ ] s3:PutObject (audio and PDF buckets)
  - [ ] s3:GetObject (audio and PDF buckets)
  - [ ] secretsmanager:GetSecretValue

- [ ] **ECS Execution Role Created** with permissions for:
  - [ ] ecr:GetAuthorizationToken
  - [ ] ecr:BatchCheckLayerAvailability
  - [ ] ecr:GetDownloadUrlForLayer
  - [ ] ecr:BatchGetImage
  - [ ] logs:CreateLogStream
  - [ ] logs:PutLogEvents

### 3. Application Configuration

- [ ] **Environment Variables Configured**
  - [ ] AWS_REGION
  - [ ] AWS_COGNITO_USER_POOL_ID
  - [ ] AWS_COGNITO_CLIENT_ID
  - [ ] AWS_COGNITO_CLIENT_SECRET (if using)
  - [ ] S3_AUDIO_BUCKET
  - [ ] S3_PDF_BUCKET
  - [ ] DB_SECRET_NAME
  - [ ] FLASK_SECRET_NAME
  - [ ] JWT_SECRET_NAME
  - [ ] CORS_ALLOWED_ORIGINS
  - [ ] LOG_LEVEL
  - [ ] FLASK_ENV=production

- [ ] **Dependencies Installed**
  - [ ] requirements.txt reviewed
  - [ ] All packages compatible with Python version
  - [ ] No security vulnerabilities in dependencies

## Local Testing

### 4. Local Development Testing

- [ ] **Environment Setup**
  - [ ] .env file created from .env.example
  - [ ] All required variables set
  - [ ] AWS credentials configured (aws configure)
  - [ ] Dependencies installed (pip install -r requirements.txt)

- [ ] **Application Startup**
  - [ ] Application starts without errors
  - [ ] All AWS services initialize successfully
  - [ ] Database connection established
  - [ ] Tables created automatically

- [ ] **Health Check**
  - [ ] /health endpoint returns 200
  - [ ] Database check passes
  - [ ] Secrets Manager check passes

- [ ] **Authentication Flow**
  - [ ] User registration works
  - [ ] Email verification code received
  - [ ] User verification works
  - [ ] User login works
  - [ ] Token refresh works
  - [ ] User logout works

- [ ] **Audio & Transcription**
  - [ ] Audio file upload works (test with sample.mp3)
  - [ ] File validation works (format and size)
  - [ ] Transcription job starts
  - [ ] Job status polling works
  - [ ] Transcript retrieval works
  - [ ] Medical entities extracted

- [ ] **Prescriptions**
  - [ ] Prescription creation works
  - [ ] PDF upload to S3 works
  - [ ] Prescription stored in database
  - [ ] Presigned URL generation works
  - [ ] PDF download works

- [ ] **Error Handling**
  - [ ] Invalid credentials handled
  - [ ] File size limit enforced
  - [ ] Unsupported file format rejected
  - [ ] Database errors handled gracefully
  - [ ] AWS service errors logged properly

## Production Deployment

### 5. Docker Image

- [ ] **Dockerfile Created**
  - [ ] Base image selected (python:3.9-slim)
  - [ ] Dependencies installed
  - [ ] Application code copied
  - [ ] Proper user permissions set
  - [ ] Health check configured

- [ ] **Image Build & Test**
  - [ ] Docker image builds successfully
  - [ ] Image size optimized
  - [ ] Container runs locally
  - [ ] Health check passes in container

- [ ] **ECR Repository**
  - [ ] ECR repository created
  - [ ] Image tagged correctly
  - [ ] Image pushed to ECR
  - [ ] Image scan completed (no critical vulnerabilities)

### 6. ECS Deployment

- [ ] **ECS Cluster**
  - [ ] Cluster created
  - [ ] Capacity provider configured (Fargate or EC2)

- [ ] **Task Definition**
  - [ ] Container image URI set
  - [ ] CPU and memory allocated
  - [ ] Environment variables configured
  - [ ] Task role ARN set
  - [ ] Execution role ARN set
  - [ ] CloudWatch logs configured
  - [ ] Health check configured

- [ ] **Service Configuration**
  - [ ] Service created
  - [ ] Desired count set
  - [ ] Load balancer configured
  - [ ] Target group health checks configured
  - [ ] Auto-scaling configured (optional)

- [ ] **Load Balancer**
  - [ ] ALB created
  - [ ] HTTPS listener configured
  - [ ] SSL certificate attached
  - [ ] Target group created
  - [ ] Health check path set to /health

### 7. Monitoring & Logging

- [ ] **CloudWatch Logs**
  - [ ] Log group created
  - [ ] Log retention period set
  - [ ] Logs streaming from application
  - [ ] JSON format validated

- [ ] **CloudWatch Alarms**
  - [ ] High error rate alarm
  - [ ] High latency alarm
  - [ ] Database connection failures
  - [ ] ECS service health alarm
  - [ ] SNS topic for notifications

- [ ] **CloudWatch Dashboards**
  - [ ] Request metrics
  - [ ] Error rates
  - [ ] Latency metrics
  - [ ] AWS service usage
  - [ ] Database metrics

### 8. Security

- [ ] **Network Security**
  - [ ] VPC configured with private subnets
  - [ ] Security groups restrict access
  - [ ] RDS not publicly accessible
  - [ ] S3 buckets not public
  - [ ] HTTPS enforced

- [ ] **Application Security**
  - [ ] Secrets not in code or logs
  - [ ] CORS properly configured
  - [ ] Input validation implemented
  - [ ] Error messages don't expose internals
  - [ ] Session management secure

- [ ] **Compliance**
  - [ ] HIPAA compliance reviewed (if applicable)
  - [ ] Data encryption at rest
  - [ ] Data encryption in transit
  - [ ] Audit logging enabled
  - [ ] Access controls documented

## Post-Deployment

### 9. Smoke Tests

- [ ] **Basic Functionality**
  - [ ] Application accessible via ALB
  - [ ] Health check returns healthy
  - [ ] User can register
  - [ ] User can login
  - [ ] Audio upload works
  - [ ] Transcription works
  - [ ] Prescription creation works

- [ ] **Performance**
  - [ ] Response times acceptable (<2s)
  - [ ] No memory leaks
  - [ ] Database connections stable
  - [ ] No error spikes

### 10. Monitoring Setup

- [ ] **Alerts Configured**
  - [ ] Email notifications set up
  - [ ] Slack/Teams integration (optional)
  - [ ] On-call rotation defined
  - [ ] Escalation procedures documented

- [ ] **Logging Review**
  - [ ] Logs readable and useful
  - [ ] No sensitive data in logs
  - [ ] Log levels appropriate
  - [ ] Request IDs present

### 11. Documentation

- [ ] **Runbooks Created**
  - [ ] Deployment procedure
  - [ ] Rollback procedure
  - [ ] Common issues and solutions
  - [ ] Emergency contacts

- [ ] **User Documentation**
  - [ ] API documentation published
  - [ ] User guides created
  - [ ] FAQ documented
  - [ ] Support channels defined

### 12. Backup & Recovery

- [ ] **Database Backups**
  - [ ] Automated backups enabled
  - [ ] Backup retention configured
  - [ ] Restore procedure tested
  - [ ] Point-in-time recovery enabled

- [ ] **Disaster Recovery**
  - [ ] Multi-AZ deployment (optional)
  - [ ] Cross-region replication (optional)
  - [ ] Recovery time objective (RTO) defined
  - [ ] Recovery point objective (RPO) defined

## Final Checks

### 13. Pre-Launch

- [ ] **Stakeholder Approval**
  - [ ] Technical review completed
  - [ ] Security review completed
  - [ ] Compliance review completed
  - [ ] Business approval obtained

- [ ] **Communication**
  - [ ] Launch date communicated
  - [ ] Maintenance window scheduled
  - [ ] Users notified (if applicable)
  - [ ] Support team briefed

### 14. Launch

- [ ] **Deployment**
  - [ ] Deploy during low-traffic period
  - [ ] Monitor logs during deployment
  - [ ] Verify health checks pass
  - [ ] Test critical paths

- [ ] **Post-Launch Monitoring**
  - [ ] Monitor for 24 hours
  - [ ] Check error rates
  - [ ] Review performance metrics
  - [ ] Gather user feedback

## Rollback Plan

### If Issues Occur

- [ ] **Immediate Actions**
  - [ ] Stop new deployments
  - [ ] Assess impact and severity
  - [ ] Notify stakeholders
  - [ ] Check logs for errors

- [ ] **Rollback Procedure**
  - [ ] Revert to previous ECS task definition
  - [ ] Verify health checks pass
  - [ ] Test critical functionality
  - [ ] Monitor for stability

- [ ] **Post-Incident**
  - [ ] Document what went wrong
  - [ ] Identify root cause
  - [ ] Create action items
  - [ ] Update procedures

## Cost Optimization

### 15. Cost Review

- [ ] **Resource Sizing**
  - [ ] ECS task size appropriate
  - [ ] RDS instance size appropriate
  - [ ] S3 lifecycle policies configured
  - [ ] CloudWatch log retention optimized

- [ ] **Monitoring**
  - [ ] Cost alerts configured
  - [ ] Usage patterns analyzed
  - [ ] Reserved instances considered (if applicable)
  - [ ] Savings plans evaluated

## Maintenance

### 16. Ongoing Tasks

- [ ] **Regular Updates**
  - [ ] Security patches applied
  - [ ] Dependencies updated
  - [ ] AWS service updates reviewed
  - [ ] Documentation kept current

- [ ] **Performance Tuning**
  - [ ] Query optimization
  - [ ] Cache implementation (if needed)
  - [ ] Connection pool tuning
  - [ ] Resource scaling

---

## Sign-Off

- [ ] **Technical Lead**: _________________ Date: _______
- [ ] **Security Team**: _________________ Date: _______
- [ ] **DevOps Team**: _________________ Date: _______
- [ ] **Product Owner**: _________________ Date: _______

---

**Notes:**
- This checklist should be reviewed and updated regularly
- Not all items may apply to your specific deployment
- Add custom items as needed for your organization
- Keep a copy of completed checklists for audit purposes
