# Provider Configuration
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

# Data Sources
data "aws_caller_identity" "current" {}

locals {
  route53_zone_name         = var.route53_zone_name != "" ? var.route53_zone_name : var.acm_domain_name
  use_auto_route53_zone     = var.acm_zone_id == "" && var.create_route53_zone && local.route53_zone_name != ""
  has_route53_zone          = var.acm_zone_id != "" || local.use_auto_route53_zone
  effective_route53_zone_id = var.acm_zone_id != "" ? var.acm_zone_id : (local.use_auto_route53_zone ? aws_route53_zone.primary[0].zone_id : "")
  www_domain_name           = var.create_www_record && var.acm_domain_name != "" && !startswith(var.acm_domain_name, "www.") ? "www.${var.acm_domain_name}" : ""
  cert_validation_domains   = local.www_domain_name != "" ? toset([var.acm_domain_name, local.www_domain_name]) : toset([var.acm_domain_name])
}

# Optional Route53 hosted zone creation (for new domains)
resource "aws_route53_zone" "primary" {
  count = local.use_auto_route53_zone ? 1 : 0
  name  = local.route53_zone_name

  tags = {
    Name        = local.route53_zone_name
    Project     = var.project_name
    Environment = var.env_name
  }
}

# ACM Certificate (optional; requires a domain you control)
resource "aws_acm_certificate" "alb" {
  count             = var.acm_domain_name != "" ? 1 : 0
  domain_name       = var.acm_domain_name
  subject_alternative_names = local.www_domain_name != "" ? [local.www_domain_name] : []
  validation_method = "DNS"

  tags = {
    Name        = "${var.project_name}-${var.env_name}-alb-cert"
    Project     = var.project_name
    Environment = var.env_name
  }
}

# DNS validation (optional; only if a hosted zone is provided)
resource "aws_route53_record" "alb_cert_validation" {
  for_each = var.acm_domain_name != "" && local.has_route53_zone ? { for domain in local.cert_validation_domains : domain => domain } : {}
  zone_id = local.effective_route53_zone_id

  name = one([
    for dvo in tolist(aws_acm_certificate.alb[0].domain_validation_options) : dvo.resource_record_name
    if dvo.domain_name == each.key
  ])
  type = one([
    for dvo in tolist(aws_acm_certificate.alb[0].domain_validation_options) : dvo.resource_record_type
    if dvo.domain_name == each.key
  ])
  ttl             = 60
  allow_overwrite = true
  records = [one([
    for dvo in tolist(aws_acm_certificate.alb[0].domain_validation_options) : dvo.resource_record_value
    if dvo.domain_name == each.key
  ])]
}

resource "aws_acm_certificate_validation" "alb" {
  count                   = var.acm_domain_name != "" && local.has_route53_zone ? 1 : 0
  certificate_arn         = aws_acm_certificate.alb[0].arn
  validation_record_fqdns = [for record in aws_route53_record.alb_cert_validation : record.fqdn]
}

# Route53 A record to route domain traffic to ALB
resource "aws_route53_record" "alb_domain_a" {
  count   = var.acm_domain_name != "" && local.has_route53_zone ? 1 : 0
  zone_id = local.effective_route53_zone_id
  name    = var.acm_domain_name
  type    = "A"

  alias {
    name                   = module.alb.alb_dns_name
    zone_id                = module.alb.alb_zone_id
    evaluate_target_health = true
  }
}

# Route53 AAAA record to route domain traffic to ALB (IPv6)
resource "aws_route53_record" "alb_domain_aaaa" {
  count   = var.acm_domain_name != "" && local.has_route53_zone ? 1 : 0
  zone_id = local.effective_route53_zone_id
  name    = var.acm_domain_name
  type    = "AAAA"

  alias {
    name                   = module.alb.alb_dns_name
    zone_id                = module.alb.alb_zone_id
    evaluate_target_health = true
  }
}

# Route53 A record for www domain
resource "aws_route53_record" "alb_domain_www_a" {
  count   = local.www_domain_name != "" && local.has_route53_zone ? 1 : 0
  zone_id = local.effective_route53_zone_id
  name    = local.www_domain_name
  type    = "A"

  alias {
    name                   = module.alb.alb_dns_name
    zone_id                = module.alb.alb_zone_id
    evaluate_target_health = true
  }
}

# Route53 AAAA record for www domain
resource "aws_route53_record" "alb_domain_www_aaaa" {
  count   = local.www_domain_name != "" && local.has_route53_zone ? 1 : 0
  zone_id = local.effective_route53_zone_id
  name    = local.www_domain_name
  type    = "AAAA"

  alias {
    name                   = module.alb.alb_dns_name
    zone_id                = module.alb.alb_zone_id
    evaluate_target_health = true
  }
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

locals {
  prescription_pdf_lambda_name = var.prescription_pdf_lambda_name != "" ? var.prescription_pdf_lambda_name : "${var.project_name}-${var.env_name}-prescription-pdf"
}

resource "aws_iam_role" "prescription_pdf_lambda" {
  count = var.enable_prescription_pdf_lambda ? 1 : 0

  name = "${local.prescription_pdf_lambda_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "${local.prescription_pdf_lambda_name}-role"
    Project     = var.project_name
    Environment = var.env_name
  }
}

resource "aws_iam_role_policy" "prescription_pdf_lambda" {
  count = var.enable_prescription_pdf_lambda ? 1 : 0

  name = "${local.prescription_pdf_lambda_name}-policy"
  role = aws_iam_role.prescription_pdf_lambda[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = "${module.s3_pdf.bucket_arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = module.s3_pdf.bucket_arn
      }
    ]
  })
}

resource "aws_lambda_function" "prescription_pdf" {
  count = var.enable_prescription_pdf_lambda ? 1 : 0

  function_name    = local.prescription_pdf_lambda_name
  role             = aws_iam_role.prescription_pdf_lambda[0].arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  filename         = var.prescription_pdf_lambda_zip_path
  source_code_hash = filebase64sha256(var.prescription_pdf_lambda_zip_path)
  timeout          = var.prescription_pdf_lambda_timeout
  memory_size      = var.prescription_pdf_lambda_memory_mb

  environment {
    variables = {
      PDF_BUCKET = module.s3_pdf.bucket_id
    }
  }

  depends_on = [aws_iam_role_policy.prescription_pdf_lambda]
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
  health_check_path = "/health/live"
  target_port       = local.container_port
  project_name      = var.project_name
  env_name          = var.env_name
}

# IAM Module
module "iam" {
  source = "./modules/iam"

  project_name                  = var.project_name
  env_name                      = var.env_name
  s3_pdf_bucket_arn             = module.s3_pdf.bucket_arn
  s3_audio_bucket_arn           = module.s3_audio.bucket_arn
  enable_prescription_pdf_lambda = var.enable_prescription_pdf_lambda
  prescription_pdf_lambda_arn = try(aws_lambda_function.prescription_pdf[0].arn, "")
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
    FLASK_ENV                 = var.env_name
    LOG_LEVEL                 = var.log_level
    LOG_VIEW_TOKEN            = var.log_view_token
    LOG_FILE_PATH             = var.log_file_path
    AWS_REGION                = var.aws_region
    AWS_TRANSCRIBE_REGION     = var.aws_region
    AWS_COMPREHEND_REGION     = var.comprehend_region
    BEDROCK_REGION            = var.bedrock_region
    BEDROCK_MODEL_ID          = var.bedrock_model_id
    CLOUDWATCH_LOG_GROUP_NAME = "/ecs/${var.project_name}-${var.env_name}"
    AWS_CLOUDWATCH_REGION     = var.aws_region
    EVENTLET_NO_GREENDNS      = "yes"
    AWS_COGNITO_USER_POOL_ID  = module.cognito.user_pool_id
    AWS_COGNITO_CLIENT_ID     = module.cognito.app_client_id
    S3_AUDIO_BUCKET           = module.s3_audio.bucket_id
    S3_PDF_BUCKET             = module.s3_pdf.bucket_id
    DB_SECRET_NAME            = module.secrets.db_secret_name
    FLASK_SECRET_NAME         = module.secrets.flask_secret_name
    JWT_SECRET_NAME           = module.secrets.jwt_secret_name
    CORS_ALLOWED_ORIGINS      = join(",", var.cors_origins)
    ENABLE_COMPREHEND_MEDICAL = var.enable_comprehend_medical ? "true" : "false"
    STREAM_IDLE_TIMEOUT_SECONDS = tostring(var.stream_idle_timeout_seconds)
    PRESCRIPTION_PDF_LAMBDA_NAME = try(aws_lambda_function.prescription_pdf[0].function_name, "")
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


# Automated ECS Testing
# Runs extraction pipeline test after ECS deployment to verify IAM policy fix
resource "null_resource" "ecs_extraction_test" {
  # Trigger test when ECS service or IAM policy changes
  triggers = {
    ecs_service_id = module.ecs.service_id
    iam_policy_hash = filemd5("${path.module}/iam_policies/bedrock_comprehend_policy.json")
  }

  provisioner "local-exec" {
    command     = "bash ${path.module}/scripts/test_ecs_extraction.sh"
    working_dir = path.module
    
    environment = {
      AWS_REGION   = var.aws_region
      ALB_DNS      = module.alb.alb_dns_name
      API_BASE_URL = var.enable_https ? "https://${var.acm_domain_name != "" ? var.acm_domain_name : module.alb.alb_dns_name}" : "http://${module.alb.alb_dns_name}"
      CLUSTER_NAME = module.ecs.cluster_name
      SERVICE_NAME = module.ecs.service_name
    }
  }

  depends_on = [
    module.ecs,
    module.alb,
    module.iam
  ]
}
