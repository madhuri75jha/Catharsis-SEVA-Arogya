output "db_secret_arn" {
  description = "ARN of the database credentials secret"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

output "flask_secret_arn" {
  description = "ARN of the Flask secret key secret"
  value       = aws_secretsmanager_secret.flask_secret.arn
}

output "jwt_secret_arn" {
  description = "ARN of the JWT secret"
  value       = aws_secretsmanager_secret.jwt_secret.arn
}
