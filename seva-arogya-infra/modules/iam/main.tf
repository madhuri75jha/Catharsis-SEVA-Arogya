# ECS Execution Role
resource "aws_iam_role" "ecs_execution" {
  name = "${var.project_name}-${var.env_name}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.env_name}-ecs-execution-role"
    Project     = var.project_name
    Environment = var.env_name
  }
}

# ECS Execution Role Policy - ECR Access
resource "aws_iam_role_policy" "ecs_execution_ecr" {
  name = "ecr-access"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      }
    ]
  })
}

# ECS Execution Role Policy - CloudWatch Logs
resource "aws_iam_role_policy" "ecs_execution_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${var.log_group_arn}:*"
      }
    ]
  })
}

# ECS Execution Role Policy - Secrets Manager
resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "secrets-manager"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = var.secrets_arns
      }
    ]
  })
}

# ECS Task Role
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-${var.env_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.env_name}-ecs-task-role"
    Project     = var.project_name
    Environment = var.env_name
  }
}

# ECS Task Role Policy - S3 Access
resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "s3-access"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${var.s3_pdf_bucket_arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = var.s3_pdf_bucket_arn
      }
    ]
  })
}

# ECS Task Role Policy - Medical AI Services
resource "aws_iam_role_policy" "ecs_task_medical_ai" {
  name = "medical-ai-access"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "transcribe:StartMedicalTranscriptionJob",
          "transcribe:GetMedicalTranscriptionJob",
          "comprehendmedical:DetectEntitiesV2",
          "comprehendmedical:InferICD10CM",
          "translate:TranslateText"
        ]
        Resource = "*"
      }
    ]
  })
}
