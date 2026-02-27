locals {
  # Common tags applied to all resources
  common_tags = {
    Project     = var.project_name
    Environment = var.env_name
    ManagedBy   = "Terraform"
  }

  # Availability zones for the region
  availability_zones = ["${var.aws_region}a", "${var.aws_region}b"]

  # VPC CIDR and subnet configuration
  vpc_cidr             = "10.0.0.0/16"
  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs = ["10.0.11.0/24", "10.0.12.0/24"]

  # Resource naming
  cluster_name = "${var.project_name}-${var.env_name}-cluster"
  service_name = "${var.project_name}-${var.env_name}-api"
  task_family  = "${var.project_name}-${var.env_name}-task"

  # Container configuration
  container_port = 5000
  cpu            = "512"
  memory         = "1024"

  # Database configuration
  db_identifier = "${var.project_name}-${var.env_name}-db"
  db_port       = 5432

  # S3 bucket names (must be globally unique)
  pdf_bucket_name   = "${var.project_name}-${var.env_name}-pdf-${data.aws_caller_identity.current.account_id}"
  audio_bucket_name = "${var.project_name}-${var.env_name}-audio-${data.aws_caller_identity.current.account_id}"
}
