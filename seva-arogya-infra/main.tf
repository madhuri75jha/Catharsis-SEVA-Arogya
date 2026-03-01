# Provider Configuration
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

# Data Sources
data "aws_caller_identity" "current" {}

# ACM Certificate (optional; requires a domain you control)
resource "aws_acm_certificate" "alb" {
  count             = var.acm_domain_name != "" ? 1 : 0
  domain_name       = var.acm_domain_name
  validation_method = "DNS"

  tags = {
    Name        = "${var.project_name}-${var.env_name}-alb-cert"
    Project     = var.project_name
    Environment = var.env_name
  }
}

# DNS validation (optional; only if a hosted zone is provided)
resource "aws_route53_record" "alb_cert_validation" {
  count   = var.acm_domain_name != "" && var.acm_zone_id != "" ? 1 : 0
  zone_id = var.acm_zone_id

  name    = tolist(aws_acm_certificate.alb[0].domain_validation_options)[0].resource_record_name
  type    = tolist(aws_acm_certificate.alb[0].domain_validation_options)[0].resource_record_type
  ttl     = 60
  records = [tolist(aws_acm_certificate.alb[0].domain_validation_options)[0].resource_record_value]
}

resource "aws_acm_certificate_validation" "alb" {
  count                   = var.acm_domain_name != "" && var.acm_zone_id != "" ? 1 : 0
  certificate_arn         = aws_acm_certificate.alb[0].arn
  validation_record_fqdns = [aws_route53_record.alb_cert_validation[0].fqdn]
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  vpc_cidr             = local.vpc_cidr
  availability_zones   = local.availability_zones
  public_subnet_cidrs  = local.public_subnet_cidrs
  private_subnet_cidrs = local.private_subnet_cidrs
  enable_nat_gateway   = true
  single_nat_gateway   = true
  project_name         = var.project_name
  env_name             = var.env_name
}

# S3 PDF Bucket Module
module "s3_pdf" {
  source = "./modules/s3"

  bucket_name          = local.pdf_bucket_name
  enable_versioning    = false
  enable_encryption    = true
  block_public_access  = true
  cors_allowed_origins = var.cors_origins
  cors_allowed_methods = ["GET", "PUT", "POST", "DELETE"]
  project_name         = var.project_name
  env_name             = var.env_name
}

# S3 Audio Bucket Module
module "s3_audio" {
  source = "./modules/s3"

  bucket_name          = local.audio_bucket_name
  enable_versioning    = false
  enable_encryption    = true
  block_public_access  = true
  cors_allowed_origins = var.cors_origins
  cors_allowed_methods = ["GET", "PUT", "POST", "DELETE"]
  project_name         = var.project_name
  env_name             = var.env_name
}

# RDS Module
module "rds" {
  source = "./modules/rds"

  identifier              = local.db_identifier
  engine_version          = var.db_engine_version != "" ? var.db_engine_version : null
  instance_class          = "db.t4g.micro"
  allocated_storage       = 20
  db_name                 = var.db_name
  master_username         = var.db_username
  master_password         = var.db_password
  vpc_id                  = module.vpc.vpc_id
  private_subnet_ids      = module.vpc.private_subnet_ids
  allowed_cidr_blocks     = local.private_subnet_cidrs
  backup_retention_period = 1
  multi_az                = false
  skip_final_snapshot     = true
  project_name            = var.project_name
  env_name                = var.env_name
}

# Cognito Module
module "cognito" {
  source = "./modules/cognito"

  user_pool_name             = "${var.project_name}-${var.env_name}-users"
  app_client_name            = "${var.project_name}-${var.env_name}-client"
  password_minimum_length    = 8
  password_require_lowercase = true
  password_require_uppercase = true
  password_require_numbers   = true
  password_require_symbols   = true
  mfa_configuration          = "OFF"
  email_verification_message = "Your verification code is {####}"
  email_verification_subject = "SEVA Arogya Verification Code"
  project_name               = var.project_name
  env_name                   = var.env_name
}

# Secrets Manager Module
module "secrets" {
  source = "./modules/secrets"

  db_credentials = {
    username = var.db_username
    password = var.db_password
    host     = module.rds.address
    port     = local.db_port
    dbname   = var.db_name
  }
  flask_secret_key = var.flask_secret_key
  jwt_secret       = var.jwt_secret
  project_name     = var.project_name
  env_name         = var.env_name

  depends_on = [module.rds]
}

# ALB Module
module "alb" {
  source = "./modules/alb"

  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  enable_https      = var.enable_https
  certificate_arn   = var.certificate_arn != "" ? var.certificate_arn : try(aws_acm_certificate.alb[0].arn, "")
  health_check_path = "/health"
  target_port       = local.container_port
  project_name      = var.project_name
  env_name          = var.env_name
}

# IAM Module
module "iam" {
  source = "./modules/iam"

  project_name       = var.project_name
  env_name           = var.env_name
  s3_pdf_bucket_arn  = module.s3_pdf.bucket_arn
  s3_audio_bucket_arn = module.s3_audio.bucket_arn
}

# ECS Module
module "ecs" {
  source = "./modules/ecs"

  cluster_name           = local.cluster_name
  service_name           = local.service_name
  task_family            = local.task_family
  container_image        = var.container_image
  container_port         = local.container_port
  cpu                    = local.cpu
  memory                 = local.memory
  desired_count          = 1
  vpc_id                 = module.vpc.vpc_id
  private_subnet_ids     = module.vpc.private_subnet_ids
  target_group_arn       = module.alb.target_group_arn
  execution_role_arn     = module.iam.ecs_execution_role_arn
  task_role_arn          = module.iam.ecs_task_role_arn
  alb_security_group_id  = module.alb.security_group_id
  enable_execute_command = var.enable_execute_command

  environment_variables = {
    FLASK_ENV              = var.env_name
    LOG_LEVEL              = var.log_level
    LOG_VIEW_TOKEN         = var.log_view_token
    LOG_FILE_PATH          = var.log_file_path
    AWS_REGION             = var.aws_region
    AWS_TRANSCRIBE_REGION  = var.aws_region
    AWS_COMPREHEND_REGION  = var.comprehend_region
    EVENTLET_NO_GREENDNS   = "yes"
    AWS_COGNITO_USER_POOL_ID = module.cognito.user_pool_id
    AWS_COGNITO_CLIENT_ID    = module.cognito.app_client_id
    S3_AUDIO_BUCKET        = module.s3_audio.bucket_id
    S3_PDF_BUCKET          = module.s3_pdf.bucket_id
    DB_SECRET_NAME         = module.secrets.db_secret_name
    FLASK_SECRET_NAME      = module.secrets.flask_secret_name
    JWT_SECRET_NAME        = module.secrets.jwt_secret_name
    CORS_ALLOWED_ORIGINS   = join(",", var.cors_origins)
    ENABLE_COMPREHEND_MEDICAL = var.enable_comprehend_medical ? "true" : "false"
  }

  secrets = [
    {
      name      = "DB_HOST"
      valueFrom = "${module.secrets.db_secret_arn}:host::"
    },
    {
      name      = "DB_PORT"
      valueFrom = "${module.secrets.db_secret_arn}:port::"
    },
    {
      name      = "DB_USERNAME"
      valueFrom = "${module.secrets.db_secret_arn}:username::"
    },
    {
      name      = "DB_PASSWORD"
      valueFrom = "${module.secrets.db_secret_arn}:password::"
    },
    {
      name      = "DB_NAME"
      valueFrom = "${module.secrets.db_secret_arn}:dbname::"
    },
    {
      name      = "FLASK_SECRET_KEY"
      valueFrom = module.secrets.flask_secret_arn
    },
    {
      name      = "JWT_SECRET"
      valueFrom = module.secrets.jwt_secret_arn
    }
  ]

  log_retention_days = 7
  project_name       = var.project_name
  env_name           = var.env_name

  depends_on = [module.iam, module.alb]
}

# VPC Endpoints (private connectivity to AWS services)
resource "aws_security_group" "vpc_endpoints" {
  name        = "${var.project_name}-${var.env_name}-vpc-endpoints-sg"
  description = "Security group for VPC interface endpoints"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "Allow HTTPS from ECS tasks"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [module.ecs.security_group_id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-${var.env_name}-vpc-endpoints-sg"
    Project     = var.project_name
    Environment = var.env_name
  }
}

# S3 Gateway Endpoint
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = module.vpc.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [module.vpc.private_route_table_id]

  tags = {
    Name        = "${var.project_name}-${var.env_name}-s3-endpoint"
    Project     = var.project_name
    Environment = var.env_name
  }
}

locals {
  interface_endpoints = concat(
    [
      "secretsmanager",
      "cognito-idp",
      "transcribe"
    ],
    var.comprehend_region == var.aws_region ? ["comprehendmedical"] : []
  )
}

# Interface Endpoints for private AWS service access
resource "aws_vpc_endpoint" "interface" {
  for_each            = toset(local.interface_endpoints)
  vpc_id              = module.vpc.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = module.vpc.private_subnet_ids
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-${var.env_name}-${each.value}-endpoint"
    Project     = var.project_name
    Environment = var.env_name
  }
}

