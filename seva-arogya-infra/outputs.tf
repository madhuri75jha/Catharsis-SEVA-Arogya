output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.alb.alb_dns_name
}

output "api_base_url" {
  description = "Base URL for API access"
  value       = var.enable_https ? "https://${module.alb.alb_dns_name}" : "http://${module.alb.alb_dns_name}"
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (if enabled)"
  value       = var.enable_cloudfront ? module.cloudfront[0].domain_name : "CloudFront not enabled"
}

output "frontend_bucket_name" {
  description = "S3 bucket name for frontend static assets"
  value       = module.s3_frontend.bucket_id
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
