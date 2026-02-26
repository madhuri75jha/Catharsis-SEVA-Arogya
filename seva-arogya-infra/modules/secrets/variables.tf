variable "db_credentials" {
  description = "Database credentials object"
  type = object({
    username = string
    password = string
    host     = string
    port     = number
    dbname   = string
  })
  sensitive = true
}

variable "flask_secret_key" {
  description = "Flask secret key"
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "JWT secret for token signing"
  type        = string
  sensitive   = true
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "env_name" {
  description = "Environment name for resource naming"
  type        = string
}
