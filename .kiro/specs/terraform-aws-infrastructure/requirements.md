# Requirements Document: Terraform AWS Infrastructure for SEVA Arogya

## 1. Functional Requirements

### 1.1 Repository Structure
The Terraform repository SHALL provide a complete, organized structure with the following components:
- Root configuration files (main.tf, variables.tf, outputs.tf, locals.tf, versions.tf)
- Backend configuration template (backend.tf.example)
- Modular architecture with separate modules for each AWS service
- Documentation files (README.md, .env.example)
- Utility scripts for common operations (init.sh, plan.sh, apply.sh)
- Git ignore configuration (.gitignore)

### 1.2 VPC and Networking
The infrastructure SHALL provision a Virtual Private Cloud with:
- CIDR block 10.0.0.0/16
- Two Availability Zones for high availability
- Public subnets (10.0.1.0/24, 10.0.2.0/24) for internet-facing resources
- Private subnets (10.0.11.0/24, 10.0.12.0/24) for backend services
- Single NAT Gateway for cost optimization
- Internet Gateway for public subnet connectivity
- Route tables configured for public and private subnet traffic

### 1.3 Application Load Balancer
The infrastructure SHALL provision an Application Load Balancer that:
- Deploys in public subnets across multiple AZs
- Listens on HTTP port 80 by default
- Optionally supports HTTPS port 443 when enabled
- Routes traffic to ECS Fargate tasks on port 5000
- Performs health checks on /health endpoint
- Provides DNS name for API access


### 1.4 ECS Fargate Service
The infrastructure SHALL provision an ECS Fargate service that:
- Creates an ECS cluster for container orchestration
- Provisions an ECR repository for backend Docker images
- Defines a task with 0.5 vCPU and 1GB memory
- Runs Flask API container on port 5000
- Maintains desired count of 1 task (no autoscaling)
- Deploys tasks in private subnets
- Integrates with CloudWatch Logs with 7-day retention
- Injects environment variables for AWS services configuration
- Retrieves secrets from Secrets Manager at runtime
- Implements health check endpoint at /health

### 1.5 RDS PostgreSQL Database
The infrastructure SHALL provision an RDS PostgreSQL database that:
- Uses PostgreSQL version 15.3
- Runs on db.t4g.micro or db.t3.micro instance class
- Allocates 20GB of storage
- Deploys in single-AZ configuration for cost optimization
- Places database in private subnets
- Disables public accessibility
- Enables storage encryption at rest
- Configures 1-day backup retention
- Stores credentials in Secrets Manager
- Enables CloudWatch logs for PostgreSQL and upgrade events

### 1.6 S3 Storage Buckets
The infrastructure SHALL provision S3 buckets for:
- PDF storage with private access, SSE-S3 encryption, and CORS configuration
- Frontend static assets with private access and CloudFront origin configuration
- Both buckets with public access blocked
- Appropriate CORS policies for application access

### 1.7 CloudFront Distribution
The infrastructure SHALL optionally provision a CloudFront distribution that:
- Serves React SPA from S3 frontend bucket
- Uses Origin Access Control (OAC) for secure S3 access
- Enforces HTTPS (redirects HTTP to HTTPS)
- Implements SPA routing (403/404 errors redirect to /index.html with 200 status)
- Enables IPv6 support
- Uses PriceClass_100 for cost optimization
- Enables compression for faster delivery
- Can be toggled via enable_cloudfront variable

### 1.8 Cognito Authentication
The infrastructure SHALL provision a Cognito User Pool that:
- Uses email as username
- Enforces password policy (minimum 8 characters, uppercase, lowercase, numbers, symbols)
- Disables MFA for dev environment
- Provides email verification
- Creates an app client for application integration
- Outputs user pool ID and client ID for application configuration

### 1.9 Secrets Management
The infrastructure SHALL provision Secrets Manager secrets for:
- Database credentials (username, password, host, port, dbname)
- Flask secret key for session management
- JWT secret for token signing
- All secrets encrypted at rest using AWS managed keys

### 1.10 IAM Roles and Policies
The infrastructure SHALL provision IAM roles with least-privilege permissions:
- ECS execution role for pulling ECR images, writing logs, and reading secrets
- ECS task role for S3 access (PDF bucket), Transcribe Medical, Comprehend Medical, and Translate services
- All policies scoped to specific resources where possible
- No overly permissive wildcard permissions except for regional services


### 1.11 Security Groups
The infrastructure SHALL provision security groups that:
- Allow ALB to accept HTTP/HTTPS traffic from internet
- Allow ECS tasks to accept traffic only from ALB on port 5000
- Allow RDS to accept PostgreSQL traffic only from ECS on port 5432
- Implement defense-in-depth with layered security
- Prevent direct internet access to ECS and RDS

### 1.12 Configuration Variables
The infrastructure SHALL support configuration through variables for:
- AWS region selection
- Project name and environment name
- CloudFront enablement toggle
- HTTPS enablement toggle
- Container image URI
- Database credentials and configuration
- Flask and JWT secrets
- CORS origins list
- Frontend build path

### 1.13 Infrastructure Outputs
The infrastructure SHALL output the following values:
- ALB DNS name for API access
- API base URL (constructed from ALB DNS)
- CloudFront domain name (if enabled)
- Frontend S3 bucket name
- PDF S3 bucket name
- RDS endpoint
- Cognito user pool ID
- Cognito app client ID
- ECR repository URL

### 1.14 Terraform State Management
The infrastructure SHALL support:
- Local state for quick prototyping
- Remote state in S3 with DynamoDB locking (via backend.tf.example)
- State encryption when using S3 backend
- Example backend configuration for easy setup

### 1.15 Deployment Scripts
The infrastructure SHALL provide utility scripts for:
- Terraform initialization (init.sh)
- Plan generation (plan.sh)
- Infrastructure application (apply.sh)
- Clear documentation of script usage

## 2. Non-Functional Requirements

### 2.1 Security
- All data at rest SHALL be encrypted (S3, RDS, Secrets Manager)
- All data in transit SHALL use HTTPS/TLS
- Database SHALL NOT be publicly accessible
- ECS tasks SHALL run in private subnets
- S3 buckets SHALL block all public access
- IAM roles SHALL follow principle of least privilege
- Secrets SHALL NOT be stored in plain text in Terraform code
- Security groups SHALL implement defense-in-depth

### 2.2 Cost Optimization
- Infrastructure SHALL use minimal resources suitable for dev/prototype environment
- RDS SHALL use smallest viable instance class (db.t4g.micro)
- RDS SHALL run in single-AZ configuration
- ECS tasks SHALL use minimal Fargate resources (0.5 vCPU, 1GB memory)
- Only one NAT Gateway SHALL be provisioned
- CloudWatch log retention SHALL be 7 days
- RDS backup retention SHALL be 1 day
- CloudFront SHALL use PriceClass_100


### 2.3 High Availability Foundation
- VPC SHALL span at least 2 Availability Zones
- Public and private subnets SHALL be distributed across multiple AZs
- ALB SHALL span multiple AZs
- ECS service SHALL be capable of running tasks across multiple AZs
- Infrastructure SHALL support future scaling to multi-AZ RDS

### 2.4 Maintainability
- Infrastructure SHALL be organized into reusable modules
- All resources SHALL follow consistent naming convention: ${project_name}-${env_name}-${resource_type}
- All resources SHALL be tagged with Project, Environment, and ManagedBy
- Code SHALL be well-documented with clear variable descriptions
- Modules SHALL have clear input/output interfaces

### 2.5 Terraform Compatibility
- Infrastructure SHALL require Terraform >= 1.6
- Infrastructure SHALL use AWS provider ~> 5.0
- Infrastructure SHALL use random provider ~> 3.5
- All Terraform code SHALL be valid HCL syntax
- No placeholder or TODO comments SHALL exist in production code

### 2.6 Deployment Readiness
- Infrastructure SHALL be immediately deployable without modifications
- All required files SHALL be present in repository structure
- README SHALL provide complete setup and deployment instructions
- .env.example SHALL document all required environment variables
- Scripts SHALL be executable and functional

### 2.7 Observability
- ECS tasks SHALL log to CloudWatch Logs
- RDS SHALL export PostgreSQL logs to CloudWatch
- Log retention SHALL be configured appropriately for dev environment
- Health check endpoints SHALL be configured for monitoring

### 2.8 Modularity
- Each AWS service SHALL be encapsulated in a separate module
- Modules SHALL be reusable across different environments
- Module dependencies SHALL be clearly defined
- Modules SHALL accept configuration through input variables
- Modules SHALL expose relevant outputs

### 2.9 Documentation
- README SHALL include prerequisites, setup steps, and deployment workflow
- README SHALL document how to build and push Docker images to ECR
- README SHALL document how to update ECS service with new images
- README SHALL document how to deploy frontend to S3 and invalidate CloudFront
- README SHALL include cost estimation notes
- .env.example SHALL document all required variables with descriptions

### 2.10 Idempotency
- Terraform apply SHALL be idempotent (safe to run multiple times)
- Resource updates SHALL not cause unnecessary recreation
- State management SHALL prevent resource drift

## 3. Constraints

### 3.1 Environment Scope
- Infrastructure is designed ONLY for dev/prototype environment
- NOT suitable for production use without modifications
- Single environment deployment (no multi-environment support required)

### 3.2 AWS Service Limitations
- Medical AI services (Transcribe Medical, Comprehend Medical) do not support resource-level IAM permissions
- CloudFront distribution creation/update can take 15-30 minutes
- RDS instance modifications may require downtime
- NAT Gateway is a single point of failure (acceptable for dev)

### 3.3 Cost Considerations
- NAT Gateway incurs hourly charges plus data transfer costs
- RDS instance runs continuously (consider stopping when not in use)
- CloudFront has minimum monthly charges
- ECS Fargate charges based on vCPU and memory per second

### 3.4 Terraform State
- Local state is not suitable for team collaboration
- S3 backend requires manual creation of bucket and DynamoDB table
- State file contains sensitive information (must be secured)


## 4. Acceptance Criteria

### 4.1 Repository Structure Completeness
GIVEN the Terraform repository
WHEN examining the file structure
THEN all required files SHALL exist:
- main.tf, variables.tf, outputs.tf, locals.tf, versions.tf
- backend.tf.example
- README.md, .gitignore, .env.example
- modules/vpc/, modules/alb/, modules/ecs/, modules/rds/, modules/s3/, modules/cloudfront/, modules/cognito/, modules/iam/, modules/secrets/
- scripts/init.sh, scripts/plan.sh, scripts/apply.sh

### 4.2 Terraform Validation
GIVEN the Terraform configuration
WHEN running `terraform init` and `terraform validate`
THEN the configuration SHALL pass validation without errors

### 4.3 VPC Network Isolation
GIVEN the VPC module
WHEN infrastructure is provisioned
THEN:
- VPC SHALL be created with CIDR 10.0.0.0/16
- 2 public subnets SHALL exist in different AZs
- 2 private subnets SHALL exist in different AZs
- Internet Gateway SHALL be attached to VPC
- NAT Gateway SHALL be created in one public subnet
- Private subnets SHALL route internet traffic through NAT Gateway

### 4.4 Security Group Chain
GIVEN the security groups
WHEN infrastructure is provisioned
THEN:
- ALB security group SHALL allow inbound HTTP/HTTPS from 0.0.0.0/0
- ECS security group SHALL allow inbound traffic only from ALB security group on port 5000
- RDS security group SHALL allow inbound traffic only from ECS security group on port 5432
- RDS SHALL NOT allow direct internet access

### 4.5 ECS Service Deployment
GIVEN the ECS module
WHEN infrastructure is provisioned
THEN:
- ECS cluster SHALL be created
- ECR repository SHALL be created for backend images
- Task definition SHALL specify 512 CPU and 1024 memory
- Service SHALL run 1 task in private subnets
- Task SHALL be registered with ALB target group
- CloudWatch log group SHALL be created with 7-day retention

### 4.6 RDS Database Configuration
GIVEN the RDS module
WHEN infrastructure is provisioned
THEN:
- PostgreSQL 15.3 instance SHALL be created
- Instance class SHALL be db.t4g.micro or db.t3.micro
- Storage SHALL be 20GB and encrypted
- Instance SHALL be in private subnets
- publicly_accessible SHALL be false
- Backup retention SHALL be 1 day
- Credentials SHALL be stored in Secrets Manager

### 4.7 S3 Bucket Security
GIVEN the S3 modules
WHEN buckets are provisioned
THEN:
- Both PDF and frontend buckets SHALL block all public access
- Both buckets SHALL enable server-side encryption
- PDF bucket SHALL have CORS configuration for application origins
- Frontend bucket SHALL have bucket policy allowing CloudFront access only

### 4.8 CloudFront Distribution
GIVEN the CloudFront module with enable_cloudfront = true
WHEN infrastructure is provisioned
THEN:
- Distribution SHALL be created with S3 origin
- Origin Access Control SHALL be configured
- viewer_protocol_policy SHALL be "redirect-to-https"
- Custom error responses SHALL redirect 403/404 to /index.html with 200 status
- IPv6 SHALL be enabled

### 4.9 Cognito User Pool
GIVEN the Cognito module
WHEN infrastructure is provisioned
THEN:
- User pool SHALL be created with email as username
- Password policy SHALL require 8+ characters, uppercase, lowercase, numbers, symbols
- App client SHALL be created
- User pool ID and client ID SHALL be output

### 4.10 Secrets Management
GIVEN the Secrets Manager module
WHEN infrastructure is provisioned
THEN:
- Database credentials secret SHALL contain username, password, host, port, dbname
- Flask secret key SHALL be stored
- JWT secret SHALL be stored
- All secrets SHALL be encrypted at rest
- ECS task definition SHALL reference secrets (not plain text)


### 4.11 IAM Least Privilege
GIVEN the IAM module
WHEN roles are provisioned
THEN:
- ECS execution role SHALL have permissions for ECR, CloudWatch Logs, and Secrets Manager only
- ECS task role SHALL have permissions for S3 (PDF bucket), Transcribe Medical, Comprehend Medical, and Translate only
- S3 permissions SHALL be scoped to specific bucket ARN
- No wildcard resource permissions SHALL exist except for regional services

### 4.12 Resource Tagging
GIVEN all AWS resources
WHEN infrastructure is provisioned
THEN:
- All resources SHALL have Project tag
- All resources SHALL have Environment tag
- All resources SHALL have ManagedBy = "Terraform" tag

### 4.13 Infrastructure Outputs
GIVEN the root outputs.tf
WHEN infrastructure is provisioned
THEN outputs SHALL include:
- alb_dns_name
- api_base_url
- cloudfront_domain_name (if enabled)
- frontend_bucket_name
- pdf_bucket_name
- rds_endpoint
- cognito_user_pool_id
- cognito_client_id
- ecr_repository_url

### 4.14 Variable Configuration
GIVEN the variables.tf
WHEN examining variable definitions
THEN:
- All required variables SHALL have descriptions
- Sensitive variables SHALL be marked as sensitive
- Default values SHALL be provided where appropriate
- Variable types SHALL be explicitly defined

### 4.15 Module Reusability
GIVEN any infrastructure module
WHEN examining module structure
THEN:
- Module SHALL have variables.tf with input variables
- Module SHALL have outputs.tf with relevant outputs
- Module SHALL have main.tf with resource definitions
- Module SHALL be usable standalone or as part of root configuration

### 4.16 Documentation Completeness
GIVEN the README.md
WHEN reviewing documentation
THEN README SHALL include:
- Prerequisites (Terraform version, AWS CLI, Docker)
- Setup instructions (clone, configure .env)
- Terraform workflow (init, plan, apply)
- Docker build and push instructions
- ECS service update instructions
- Frontend deployment instructions
- CloudFront invalidation instructions
- Cost estimation notes

### 4.17 Environment Variable Template
GIVEN the .env.example
WHEN reviewing the file
THEN it SHALL document:
- aws_region
- project_name and env_name
- enable_cloudfront and enable_https
- container_image
- db_name, db_username, db_password
- flask_secret_key, jwt_secret
- cors_origins
- frontend_build_path

### 4.18 Deployment Scripts Functionality
GIVEN the scripts directory
WHEN examining scripts
THEN:
- init.sh SHALL run terraform init
- plan.sh SHALL run terraform plan with output file
- apply.sh SHALL run terraform apply with plan file
- All scripts SHALL be executable (chmod +x)

### 4.19 Backend Configuration Template
GIVEN the backend.tf.example
WHEN reviewing the file
THEN it SHALL include:
- S3 backend configuration
- Bucket name placeholder
- State file key path
- Region configuration
- Encryption enabled
- DynamoDB table for state locking

### 4.20 No Placeholders or TODOs
GIVEN all Terraform files
WHEN searching for "TODO" or "PLACEHOLDER"
THEN no such comments SHALL exist in the code

### 4.21 Dependency Ordering
GIVEN the root main.tf
WHEN examining module dependencies
THEN:
- VPC SHALL be created before all other resources
- Security groups SHALL be created before resources that reference them
- RDS and Secrets Manager SHALL be created before ECS task definition
- IAM roles SHALL be created before ECS service
- ALB target group SHALL be created before ECS service
- S3 buckets SHALL be created before CloudFront distribution

### 4.22 Cost Optimization Verification
GIVEN the infrastructure configuration
WHEN reviewing resource specifications
THEN:
- RDS instance class SHALL be db.t4g.micro or db.t3.micro
- RDS multi_az SHALL be false
- ECS task CPU SHALL be "512"
- ECS task memory SHALL be "1024"
- ECS desired_count SHALL be 1
- NAT Gateway count SHALL be 1
- CloudWatch log retention SHALL be 7 days
- RDS backup retention SHALL be 1 day

### 4.23 Encryption Verification
GIVEN all storage resources
WHEN infrastructure is provisioned
THEN:
- S3 buckets SHALL have server_side_encryption_configuration enabled
- RDS instance SHALL have storage_encrypted = true
- Secrets Manager secrets SHALL be encrypted (default AWS managed key)

### 4.24 Network Accessibility Verification
GIVEN the complete infrastructure
WHEN infrastructure is provisioned
THEN:
- ALB SHALL be accessible from internet
- ECS tasks SHALL NOT be directly accessible from internet
- RDS SHALL NOT be directly accessible from internet
- RDS SHALL NOT be accessible from ALB (only from ECS)

### 4.25 End-to-End Deployment Success
GIVEN the complete Terraform repository
WHEN following README instructions from start to finish
THEN:
- Infrastructure SHALL provision successfully without errors
- Docker image SHALL push to ECR successfully
- ECS service SHALL run tasks successfully
- ALB health checks SHALL pass
- Frontend SHALL deploy to S3 successfully
- CloudFront SHALL serve frontend (if enabled)
- Application SHALL be accessible and functional

