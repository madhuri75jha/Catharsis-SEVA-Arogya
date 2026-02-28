output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.alb.alb_dns_name
}

output "api_base_url" {
  description = "Base URL for API access"
  value       = var.enable_https ? "https://${module.alb.alb_dns_name}" : "http://${module.alb.alb_dns_name}"
}

output "audio_bucket_name" {
  description = "S3 bucket name for audio storage"
  value       = module.s3_audio.bucket_id
}

output "pdf_bucket_name" {
  description = "S3 bucket name for PDF storage"
  value       = module.s3_pdf.bucket_id
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint (host:port)"
  value       = module.rds.endpoint
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = module.cognito.user_pool_id
}

output "cognito_client_id" {
  description = "Cognito App Client ID"
  value       = module.cognito.app_client_id
}

output "db_secret_name" {
  description = "Secrets Manager name for database credentials"
  value       = module.secrets.db_secret_name
}

output "flask_secret_name" {
  description = "Secrets Manager name for Flask secret key"
  value       = module.secrets.flask_secret_name
}

output "jwt_secret_name" {
  description = "Secrets Manager name for JWT secret"
  value       = module.secrets.jwt_secret_name
}

output "ecr_repository_url" {
  description = "ECR repository URL for backend Docker images"
  value       = module.ecs.ecr_repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = module.ecs.service_name
}
output "transcribe_endpoint" {
  description = "AWS Transcribe service endpoint URL"
  value       = "https://transcribe.${var.aws_region}.amazonaws.com"
}

output "transcribe_streaming_endpoint" {
  description = "AWS Transcribe streaming service endpoint URL"
  value       = "https://transcribestreaming.${var.aws_region}.amazonaws.com"
}
