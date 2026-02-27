# Database Credentials Secret
resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${var.project_name}-${var.env_name}-db-credentials"
  description = "RDS PostgreSQL database credentials"

  tags = {
    Name        = "${var.project_name}-${var.env_name}-db-credentials"
    Project     = var.project_name
    Environment = var.env_name
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id

  secret_string = jsonencode({
    username = var.db_credentials.username
    password = var.db_credentials.password
    host     = var.db_credentials.host
    port     = var.db_credentials.port
    database = var.db_credentials.dbname
    dbname   = var.db_credentials.dbname
    engine   = "postgres"
  })
}

# Flask Secret Key
resource "aws_secretsmanager_secret" "flask_secret" {
  name        = "${var.project_name}-${var.env_name}-flask-secret"
  description = "Flask secret key for session management"

  tags = {
    Name        = "${var.project_name}-${var.env_name}-flask-secret"
    Project     = var.project_name
    Environment = var.env_name
  }
}

resource "aws_secretsmanager_secret_version" "flask_secret" {
  secret_id     = aws_secretsmanager_secret.flask_secret.id
  secret_string = var.flask_secret_key
}

# JWT Secret
resource "aws_secretsmanager_secret" "jwt_secret" {
  name        = "${var.project_name}-${var.env_name}-jwt-secret"
  description = "JWT secret for token signing"

  tags = {
    Name        = "${var.project_name}-${var.env_name}-jwt-secret"
    Project     = var.project_name
    Environment = var.env_name
  }
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = var.jwt_secret
}
