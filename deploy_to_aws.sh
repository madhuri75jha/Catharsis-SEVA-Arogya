#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$ROOT_DIR/seva-arogya-infra"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

echo "========================================="
echo "SEVA Arogya - Deploy to AWS"
echo "========================================="

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: $ENV_FILE not found"
  echo "Create it from .env.example at the repo root."
  exit 1
fi

# Load env
set -a
source "$ENV_FILE"
set +a

required_vars=(
  AWS_REGION
  DB_NAME
  DB_USERNAME
  DB_PASSWORD
  FLASK_SECRET_KEY
  JWT_SECRET
  CORS_ALLOWED_ORIGINS
)

missing=0
for v in "${required_vars[@]}"; do
  if [ -z "${!v:-}" ]; then
    echo "Missing required env var: $v"
    missing=1
  fi
done

if [ "$missing" -ne 0 ]; then
  echo "Please update $ENV_FILE and re-run."
  exit 1
fi

for cmd in terraform aws docker; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: $cmd is not installed or not on PATH."
    exit 1
  fi
done

echo ""
echo "==> Running pre-deployment checks..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/scripts/pre_deploy_check.sh" ]; then
  if ! bash "$SCRIPT_DIR/scripts/pre_deploy_check.sh"; then
    echo ""
    echo "Pre-deployment checks failed. Aborting deployment."
    exit 1
  fi
else
  echo "Warning: Pre-deployment check script not found"
  echo "Proceeding without connectivity validation..."
fi

terraform_vars=(
  "-var=aws_region=${AWS_REGION}"
  "-var=project_name=${PROJECT_NAME:-seva-arogya}"
  "-var=env_name=${ENV_NAME:-dev}"
  "-var=enable_https=${ENABLE_HTTPS:-false}"
  "-var=certificate_arn=${CERTIFICATE_ARN:-}"
  "-var=acm_domain_name=${ACM_DOMAIN_NAME:-}"
  "-var=acm_zone_id=${ACM_ZONE_ID:-}"
  "-var=container_image=${CONTAINER_IMAGE:-nginx:latest}"
  "-var=db_name=${DB_NAME}"
  "-var=db_engine_version=${DB_ENGINE_VERSION:-}"
  "-var=db_username=${DB_USERNAME}"
  "-var=db_password=${DB_PASSWORD}"
  "-var=flask_secret_key=${FLASK_SECRET_KEY}"
  "-var=jwt_secret=${JWT_SECRET}"
  "-var=log_level=${LOG_LEVEL:-INFO}"
  "-var=enable_execute_command=${ENABLE_EXECUTE_COMMAND:-true}"
  "-var=log_view_token=${LOG_VIEW_TOKEN:-}"
  "-var=log_file_path=${LOG_FILE_PATH:-logs/app.log}"
  "-var=cors_origins=[\"${CORS_ALLOWED_ORIGINS}\"]"
)

echo ""
echo "==> Terraform init/plan/apply (infra)"
pushd "$INFRA_DIR" >/dev/null
terraform init
terraform plan "${terraform_vars[@]}" -out=tfplan
terraform apply tfplan
rm -f tfplan

ECR_URL="$(terraform output -raw ecr_repository_url)"
ALB_URL="$(terraform output -raw api_base_url)"
CLUSTER_NAME="$(terraform output -raw ecs_cluster_name)"
SERVICE_NAME="$(terraform output -raw ecs_service_name)"
popd >/dev/null

echo ""
echo "==> Docker build/tag/push"
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_URL"
docker build -t seva-arogya-backend "$ROOT_DIR"
docker tag seva-arogya-backend:latest "$ECR_URL:latest"
docker push "$ECR_URL:latest"

echo ""
echo "==> Terraform apply (update ECS task definition)"
pushd "$INFRA_DIR" >/dev/null
terraform apply \
  "${terraform_vars[@]}" \
  -var="container_image=${ECR_URL}:latest" \
  -auto-approve
popd >/dev/null

echo ""
echo "==> Force ECS deployment"
aws ecs update-service \
  --cluster "$CLUSTER_NAME" \
  --service "$SERVICE_NAME" \
  --force-new-deployment \
  --region "$AWS_REGION" >/dev/null

echo ""
echo "Deployment complete."
echo "API Base URL: $ALB_URL"
echo "Health check: ${ALB_URL}/health"

echo ""
echo "==> Running deployment validation..."
echo "Waiting 90 seconds for service to stabilize (NAT gateway, routes, ECS tasks)..."
sleep 90

# Run validation script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/scripts/validate_deployment.sh" ]; then
  bash "$SCRIPT_DIR/scripts/validate_deployment.sh" "$ALB_URL"
else
  echo "Warning: Validation script not found at $SCRIPT_DIR/scripts/validate_deployment.sh"
  echo "Skipping automated validation. Please manually verify:"
  echo "  curl ${ALB_URL}/health"
  echo "  curl ${ALB_URL}/health/aws-connectivity"
fi
