#!/bin/bash
# Terraform Plan Script

set -e

echo "========================================="
echo "Creating Terraform Plan"
echo "========================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found"
    echo "Please create .env from .env.example and configure your variables"
    exit 1
fi

# Load environment variables from .env
export $(grep -v '^#' .env | xargs)

# Create plan file
echo ""
echo "Running terraform plan..."
terraform plan \
  -var="aws_region=${AWS_REGION:-us-east-1}" \
  -var="project_name=${PROJECT_NAME:-seva-arogya}" \
  -var="env_name=${ENV_NAME:-dev}" \
  -var="enable_cloudfront=${ENABLE_CLOUDFRONT:-true}" \
  -var="enable_https=${ENABLE_HTTPS:-false}" \
  -var="container_image=${CONTAINER_IMAGE:-nginx:latest}" \
  -var="db_name=${DB_NAME}" \
  -var="db_username=${DB_USERNAME}" \
  -var="db_password=${DB_PASSWORD}" \
  -var="flask_secret_key=${FLASK_SECRET_KEY}" \
  -var="jwt_secret=${JWT_SECRET}" \
  -var="cors_origins=[\"${CORS_ORIGINS}\"]" \
  -out=tfplan

echo ""
echo "========================================="
echo "Plan created successfully!"
echo "========================================="
echo ""
echo "Review the plan above, then run:"
echo "  ./scripts/apply.sh"
