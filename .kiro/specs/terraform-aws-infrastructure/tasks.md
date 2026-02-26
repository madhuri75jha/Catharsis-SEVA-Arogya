# Tasks: Terraform AWS Infrastructure for SEVA Arogya

## 1. Repository Setup and Root Configuration

- [x] 1.1 Create repository root structure
- [x] 1.2 Create versions.tf with Terraform and provider requirements
- [x] 1.3 Create variables.tf with all input variables
- [x] 1.4 Create outputs.tf with all infrastructure outputs
- [x] 1.5 Create locals.tf for computed local values
- [x] 1.6 Create backend.tf.example with S3 backend configuration
- [x] 1.7 Create .gitignore for Terraform files
- [x] 1.8 Create .env.example with all required variables

## 2. VPC Module

- [x] 2.1 Create modules/vpc directory structure
- [x] 2.2 Create modules/vpc/variables.tf
- [x] 2.3 Create modules/vpc/outputs.tf
- [x] 2.4 Create modules/vpc/main.tf with VPC resource
- [x] 2.5 Add public subnets with count-based creation
- [x] 2.6 Add private subnets with count-based creation
- [x] 2.7 Add Internet Gateway
- [x] 2.8 Add NAT Gateway with Elastic IP
- [x] 2.9 Add route tables for public and private subnets
- [x] 2.10 Add route table associations

## 3. Security Groups Module

- [x] 3.1 Create security group for ALB (HTTP/HTTPS ingress)
- [x] 3.2 Create security group for ECS (ALB-only ingress on port 5000)
- [x] 3.3 Create security group for RDS (ECS-only ingress on port 5432)
- [x] 3.4 Add egress rules for all security groups

## 4. S3 Module

- [x] 4.1 Create modules/s3 directory structure
- [x] 4.2 Create modules/s3/variables.tf
- [x] 4.3 Create modules/s3/outputs.tf
- [x] 4.4 Create modules/s3/main.tf with S3 bucket resource
- [x] 4.5 Add S3 bucket public access block configuration
- [x] 4.6 Add S3 bucket server-side encryption configuration
- [x] 4.7 Add S3 bucket CORS configuration (conditional)
- [x] 4.8 Add S3 bucket versioning configuration (conditional)

## 5. RDS Module

- [x] 5.1 Create modules/rds directory structure
- [x] 5.2 Create modules/rds/variables.tf
- [x] 5.3 Create modules/rds/outputs.tf
- [x] 5.4 Create modules/rds/main.tf with DB subnet group
- [x] 5.5 Add RDS security group resource
- [x] 5.6 Add random password generation for DB password
- [x] 5.7 Add RDS PostgreSQL instance resource
- [x] 5.8 Configure RDS encryption, backups, and logging

## 6. Secrets Manager Module

- [x] 6.1 Create modules/secrets directory structure
- [x] 6.2 Create modules/secrets/variables.tf
- [x] 6.3 Create modules/secrets/outputs.tf
- [x] 6.4 Create modules/secrets/main.tf with DB credentials secret
- [x] 6.5 Add Flask secret key secret resource
- [x] 6.6 Add JWT secret resource
- [x] 6.7 Add secret versions with JSON-encoded values

## 7. IAM Module

- [x] 7.1 Create modules/iam directory structure
- [x] 7.2 Create modules/iam/variables.tf
- [x] 7.3 Create modules/iam/outputs.tf
- [x] 7.4 Create modules/iam/main.tf with ECS execution role
- [x] 7.5 Add ECS execution role policies (ECR, logs, secrets)
- [x] 7.6 Add ECS task role
- [x] 7.7 Add ECS task role S3 policy (PDF bucket access)
- [x] 7.8 Add ECS task role medical AI policy (Transcribe, Comprehend, Translate)

## 8. ALB Module

- [x] 8.1 Create modules/alb directory structure
- [x] 8.2 Create modules/alb/variables.tf
- [x] 8.3 Create modules/alb/outputs.tf
- [x] 8.4 Create modules/alb/main.tf with ALB resource
- [x] 8.5 Add ALB target group for ECS
- [x] 8.6 Add HTTP listener (port 80)
- [x] 8.7 Add HTTPS listener (port 443, conditional)
- [x] 8.8 Configure health check on target group


## 9. ECS Module

- [x] 9.1 Create modules/ecs directory structure
- [x] 9.2 Create modules/ecs/variables.tf
- [x] 9.3 Create modules/ecs/outputs.tf
- [x] 9.4 Create modules/ecs/main.tf with ECS cluster
- [x] 9.5 Add ECR repository resource
- [x] 9.6 Add CloudWatch log group for ECS
- [x] 9.7 Add ECS task definition with container definitions
- [x] 9.8 Configure task definition with environment variables
- [x] 9.9 Configure task definition with secrets from Secrets Manager
- [x] 9.10 Add health check configuration to container definition
- [x] 9.11 Add ECS service resource
- [x] 9.12 Configure ECS service network configuration (private subnets)
- [x] 9.13 Configure ECS service load balancer integration

## 10. Cognito Module

- [x] 10.1 Create modules/cognito directory structure
- [x] 10.2 Create modules/cognito/variables.tf
- [x] 10.3 Create modules/cognito/outputs.tf
- [x] 10.4 Create modules/cognito/main.tf with user pool
- [x] 10.5 Configure user pool password policy
- [x] 10.6 Configure user pool email verification
- [x] 10.7 Add Cognito user pool client resource

## 11. CloudFront Module

- [x] 11.1 Create modules/cloudfront directory structure
- [x] 11.2 Create modules/cloudfront/variables.tf
- [x] 11.3 Create modules/cloudfront/outputs.tf
- [x] 11.4 Create modules/cloudfront/main.tf with Origin Access Control
- [x] 11.5 Add CloudFront distribution resource
- [x] 11.6 Configure S3 origin with OAC
- [x] 11.7 Configure default cache behavior (HTTPS redirect, compression)
- [x] 11.8 Add custom error responses for SPA routing (403/404 → /index.html)
- [x] 11.9 Configure viewer certificate (CloudFront default)
- [x] 11.10 Add S3 bucket policy for CloudFront access

## 12. Root Main Configuration

- [x] 12.1 Create main.tf with Terraform and provider blocks
- [x] 12.2 Add VPC module instantiation
- [x] 12.3 Add S3 PDF bucket module instantiation
- [x] 12.4 Add S3 frontend bucket module instantiation
- [x] 12.5 Add RDS module instantiation with VPC dependencies
- [x] 12.6 Add Cognito module instantiation
- [x] 12.7 Add Secrets Manager module instantiation with RDS dependencies
- [x] 12.8 Add IAM module instantiation
- [x] 12.9 Add ALB module instantiation with VPC dependencies
- [x] 12.10 Add ECS module instantiation with all dependencies
- [x] 12.11 Add CloudFront module instantiation (conditional)
- [x] 12.12 Configure module dependencies and data flow

## 13. Documentation

- [x] 13.1 Create README.md with overview and prerequisites
- [x] 13.2 Document Terraform setup steps (init, plan, apply)
- [x] 13.3 Document Docker build and ECR push workflow
- [x] 13.4 Document ECS service update procedure
- [x] 13.5 Document frontend deployment to S3
- [x] 13.6 Document CloudFront invalidation procedure
- [x] 13.7 Add cost estimation notes
- [x] 13.8 Add troubleshooting section
- [x] 13.9 Document environment variable configuration
- [x] 13.10 Add architecture diagram or reference

## 14. Utility Scripts

- [x] 14.1 Create scripts directory
- [x] 14.2 Create scripts/init.sh for Terraform initialization
- [x] 14.3 Create scripts/plan.sh for Terraform plan generation
- [x] 14.4 Create scripts/apply.sh for Terraform apply
- [x] 14.5 Make all scripts executable (chmod +x)

## 15. Testing and Validation

- [x] 15.1 Run terraform init to verify configuration
- [x] 15.2 Run terraform validate to check syntax
- [x] 15.3 Run terraform fmt to format code
- [x] 15.4 Verify all module outputs are properly wired
- [x] 15.5 Verify security group dependencies are correct
- [x] 15.6 Verify IAM policies follow least privilege
- [x] 15.7 Verify all resources have required tags
- [x] 15.8 Verify encryption is enabled on all storage resources
- [x] 15.9 Verify no secrets are in plain text
- [x] 15.10 Verify no TODO or PLACEHOLDER comments exist

## 16. Final Review

- [x] 16.1 Verify all acceptance criteria are met
- [x] 16.2 Verify repository structure matches specification
- [x] 16.3 Verify all required files exist
- [x] 16.4 Verify documentation is complete and accurate
- [x] 16.5 Verify code follows Terraform best practices
- [x] 16.6 Verify cost optimization settings are applied
- [x] 16.7 Verify security best practices are implemented
- [x] 16.8 Perform final code review

