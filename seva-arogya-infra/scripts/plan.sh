#!/bin/bash
# Terraform Plan Script

set -e

echo "========================================="
echo "Creating Terraform Plan"
echo "========================================="

# Check if .env file exists (shared at repo root)
ENV_FILE="${ENV_FILE:-../.env}"
if [ ! -f "$ENV_FILE" ]; then
    echo "Warning: $ENV_FILE file not found"
    echo "Please create .env from .env.example at the repo root and configure your variables"
    exit 1
fi

# Load environment variables from .env
set -a
source "$ENV_FILE"
set +a

# Create plan file
echo ""
echo "Running terraform plan..."
terraform plan \
  -var="aws_region=${AWS_REGION:-us-east-1}" \
  -var="project_name=${PROJECT_NAME:-seva-arogya}" \
  -var="env_name=${ENV_NAME:-dev}" \
  -var="enable_https=${ENABLE_HTTPS:-false}" \
  -var="container_image=${CONTAINER_IMAGE:-nginx:latest}" \
  -var="db_name=${DB_NAME}" \
  -var="db_username=${DB_USERNAME}" \
  -var="db_password=${DB_PASSWORD}" \
  -var="flask_secret_key=${FLASK_SECRET_KEY}" \
  -var="jwt_secret=${JWT_SECRET}" \
  -var="log_level=${LOG_LEVEL:-INFO}" \
  -var="cors_origins=[\"${CORS_ALLOWED_ORIGINS}\"]" \
  -out=tfplan

echo ""
echo "========================================="
echo "Plan created successfully!"
echo "========================================="
echo ""
echo "Review the plan above, then run:"
echo "  ./scripts/apply.sh"
