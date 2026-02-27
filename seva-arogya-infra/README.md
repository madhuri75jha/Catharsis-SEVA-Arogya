# SEVA Arogya AWS Infrastructure (Terraform)

Complete Terraform infrastructure for deploying SEVA Arogya prototype/dev environment on AWS.

## Architecture Overview

This infrastructure provisions:
- **VPC**: 10.0.0.0/16 with public and private subnets across 2 AZs
- **ECS Fargate**: Flask API backend with 0.5 vCPU / 1GB memory
- **RDS PostgreSQL**: Single-AZ db.t4g.micro instance with 20GB storage
- **ALB**: Application Load Balancer for API traffic
- **S3**: Buckets for audio and PDF storage
- **Cognito**: User Pool for authentication
- **Secrets Manager**: Secure storage for database credentials and app secrets
- **IAM**: Least-privilege roles for ECS tasks

## Prerequisites

- **Terraform** >= 1.6 ([Install](https://www.terraform.io/downloads))
- **AWS CLI** configured with credentials ([Install](https://aws.amazon.com/cli/))
- **Docker** for building backend images ([Install](https://docs.docker.com/get-docker/))
- AWS account with appropriate permissions

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url> seva-arogya-infra
cd seva-arogya-infra

# Copy environment template (at repo root)
cp ../.env.example ../.env

# Edit .env with your values
nano ../.env
```

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Plan Infrastructure

```bash
terraform plan -out=tfplan
```

### 4. Apply Infrastructure

```bash
terraform apply tfplan
```

This will take 10-15 minutes. Note the outputs - you'll need them for deployment.

## Environment Variables

Configure these in the repo root `.env` before running Terraform:

```bash
# AWS Configuration
AWS_REGION=us-east-1

# Project Configuration
PROJECT_NAME=seva-arogya
ENV_NAME=dev

# Feature Toggles
ENABLE_HTTPS=false

# Container Image (update after pushing to ECR)
CONTAINER_IMAGE=<account-id>.dkr.ecr.us-east-1.amazonaws.com/seva-arogya-dev-backend:latest

# Database Configuration
DB_NAME=sevaarogya
DB_USERNAME=sevaadmin
DB_PASSWORD=<secure-password-min-8-chars>

# Application Secrets (generate secure random strings)
FLASK_SECRET_KEY=<32-char-random-string>
JWT_SECRET=<32-char-random-string>

# CORS Origins (comma-separated)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5000

# Logging
LOG_LEVEL=INFO
```

## Deployment Workflow

### Step 1: Deploy Infrastructure

```bash
terraform apply
```

### Step 2: Build and Push Backend Docker Image

```bash
# Get ECR repository URL from Terraform output
ECR_URL=$(terraform output -raw ecr_repository_url)

# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URL

# Build Docker image (from your backend directory)
cd ..
docker build -t seva-arogya-backend .

# Tag and push to ECR
docker tag seva-arogya-backend:latest $ECR_URL:latest
docker push $ECR_URL:latest
```

### Step 3: Update ECS Service

After pushing the image, force ECS to deploy the new version:

```bash
aws ecs update-service \
  --cluster seva-arogya-dev-cluster \
  --service seva-arogya-dev-api \
  --force-new-deployment \
  --region us-east-1
```

Wait 2-3 minutes for the service to stabilize. Check status:

```bash
aws ecs describe-services \
  --cluster seva-arogya-dev-cluster \
  --services seva-arogya-dev-api \
  --region us-east-1 \
  --query 'services[0].deployments'
```

## Accessing Your Application

After deployment, get the URLs:

```bash
# API endpoint
terraform output api_base_url
```

## Updating the Application

### Update Backend Code

```bash
# Rebuild and push Docker image
docker build -t seva-arogya-backend .
docker tag seva-arogya-backend:latest $ECR_URL:latest
docker push $ECR_URL:latest

# Force new deployment
aws ecs update-service \
  --cluster seva-arogya-dev-cluster \
  --service seva-arogya-dev-api \
  --force-new-deployment \
  --region us-east-1
```

## Remote State (Optional)

For team collaboration, configure remote state in S3:

```bash
# Create S3 bucket for state
aws s3api create-bucket \
  --bucket seva-arogya-terraform-state \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket seva-arogya-terraform-state \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket seva-arogya-terraform-state \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Create DynamoDB table for locking
aws dynamodb create-table \
  --table-name seva-arogya-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1

# Rename backend.tf.example to backend.tf
mv backend.tf.example backend.tf

# Migrate state
terraform init -migrate-state
```

## Cost Estimation

Approximate monthly costs for dev environment (us-east-1):

- **NAT Gateway**: ~$32/month + data transfer
- **RDS db.t4g.micro**: ~$12/month (single-AZ)
- **ECS Fargate** (0.5 vCPU, 1GB): ~$15/month (24/7)
- **ALB**: ~$16/month + LCU charges
- **S3**: <$1/month (low storage)
- **Secrets Manager**: ~$1.20/month (3 secrets)

**Total**: ~$72-80/month

**Cost Optimization Tips**:
- Stop RDS instance when not in use: `aws rds stop-db-instance --db-instance-identifier seva-arogya-dev-db`
- Scale ECS to 0 tasks when not in use: `aws ecs update-service --cluster seva-arogya-dev-cluster --service seva-arogya-dev-api --desired-count 0`

## Troubleshooting

### ECS Tasks Not Starting

Check ECS service events:
```bash
aws ecs describe-services \
  --cluster seva-arogya-dev-cluster \
  --services seva-arogya-dev-api \
  --query 'services[0].events[0:5]'
```

Check CloudWatch logs:
```bash
aws logs tail /ecs/seva-arogya-dev --follow
```

### ALB Health Checks Failing

Ensure your Flask app has a `/health` endpoint that returns 200 OK:

```python
@app.route('/health')
def health():
    return {'status': 'healthy'}, 200
```

### Database Connection Issues

Verify security group allows ECS to RDS:
```bash
aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=seva-arogya-dev-rds-sg" \
  --query 'SecurityGroups[0].IpPermissions'
```

### Secrets Not Loading

Verify ECS execution role has Secrets Manager permissions:
```bash
aws iam get-role-policy \
  --role-name seva-arogya-dev-ecs-execution-role \
  --policy-name secrets-manager
```

## Cleanup

To destroy all infrastructure:

```bash
# WARNING: This will delete all resources including data
terraform destroy
```

Note: You may need to manually delete:
- ECR images
- S3 bucket contents
- CloudWatch log streams

## Module Structure

```
seva-arogya-infra/
├── main.tf              # Root module orchestration
├── variables.tf         # Input variables
├── outputs.tf           # Output values
├── locals.tf            # Local values
├── versions.tf          # Terraform and provider versions
├── backend.tf.example   # Remote state configuration template
├── modules/
│   ├── vpc/            # VPC, subnets, NAT gateway
│   ├── alb/            # Application Load Balancer
│   ├── ecs/            # ECS cluster, service, task definition
│   ├── rds/            # PostgreSQL database
│   ├── s3/             # S3 buckets
│   ├── cognito/        # Cognito User Pool
│   ├── iam/            # IAM roles and policies
│   └── secrets/        # Secrets Manager
└── scripts/
    ├── init.sh         # Terraform init
    ├── plan.sh         # Terraform plan
    └── apply.sh        # Terraform apply
```

## Security Best Practices

- Database is in private subnets, not publicly accessible
- ECS tasks run in private subnets
- S3 buckets block all public access
- Secrets stored in Secrets Manager, not in code
- IAM roles follow least-privilege principle
- All data encrypted at rest (S3, RDS, Secrets Manager)
- Security groups implement defense-in-depth

## Support

For issues or questions:
1. Check CloudWatch logs: `/ecs/seva-arogya-dev`
2. Review ECS service events
3. Verify security group rules
4. Check IAM role permissions

## License

[Your License Here]
