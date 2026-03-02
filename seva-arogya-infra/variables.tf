variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-east-1"
}

variable "comprehend_region" {
  description = "AWS region for Comprehend Medical (if different from aws_region)"
  type        = string
  default     = "us-east-1"
}

variable "bedrock_region" {
  description = "AWS region for Bedrock Runtime"
  type        = string
  default     = "us-east-1"
}

variable "bedrock_model_id" {
  description = "Bedrock model ID used for extraction (must support tool/function use)"
  type        = string
  default     = "anthropic.claude-3-haiku-20240307-v1:0"
}

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "seva-arogya"
}

variable "env_name" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "enable_cloudfront" {
  description = "Enable CloudFront distribution for frontend"
  type        = bool
  default     = true
}

variable "enable_https" {
  description = "Enable HTTPS listener on ALB (requires certificate_arn)"
  type        = bool
  default     = false
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS (required if enable_https is true)"
  type        = string
  default     = ""
}

variable "acm_domain_name" {
  description = "Domain name for ACM certificate (optional; used to request a new cert)"
  type        = string
  default     = ""
}

variable "acm_zone_id" {
  description = "Route53 hosted zone ID for ACM DNS validation (optional)"
  type        = string
  default     = ""
}

variable "container_image" {
  description = "Docker image URI for ECS task (ECR repository URL with tag)"
  type        = string
  default     = "nginx:latest"
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "sevaarogya"
}

variable "db_engine_version" {
  description = "PostgreSQL engine version (leave empty to use AWS default)"
  type        = string
  default     = ""
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "sevaadmin"
  sensitive   = true
}

variable "db_password" {
  description = "PostgreSQL master password (minimum 8 characters)"
  type        = string
  sensitive   = true
}

variable "flask_secret_key" {
  description = "Flask secret key for session management"
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "JWT secret for token signing"
  type        = string
  sensitive   = true
}

variable "cors_origins" {
  description = "List of allowed CORS origins"
  type        = list(string)
  default     = ["http://localhost:3000"]
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
}

variable "enable_execute_command" {
  description = "Enable ECS Exec for the ECS service"
  type        = bool
  default     = true
}

variable "log_view_token" {
  description = "Token required to access /debug/logs"
  type        = string
  default     = ""
  sensitive   = true
}

variable "log_file_path" {
  description = "Path to application log file in the container"
  type        = string
  default     = "logs/app.log"
}

variable "enable_comprehend_medical" {
  description = "Enable Comprehend Medical connectivity checks (only in supported regions)"
  type        = bool
  default     = false
}

variable "frontend_build_path" {
  description = "Path to frontend build directory (for documentation purposes)"
  type        = string
  default     = "../seva-arogya-frontend/build"
}
