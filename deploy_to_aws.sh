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

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Error: python3/python is required to package Lambda."
  exit 1
fi

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
  "-var=create_route53_zone=${CREATE_ROUTE53_ZONE:-false}"
  "-var=route53_zone_name=${ROUTE53_ZONE_NAME:-}"
  "-var=create_www_record=${CREATE_WWW_RECORD:-true}"
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

LAMBDA_SRC_DIR="$ROOT_DIR/lambda/prescription_pdf_generator"
LAMBDA_BUILD_DIR="$INFRA_DIR/build/prescription_pdf_lambda"
LAMBDA_ZIP_PATH="$INFRA_DIR/build/prescription_pdf_lambda.zip"

echo ""
echo "==> Packaging prescription PDF Lambda"
rm -rf "$LAMBDA_BUILD_DIR"
mkdir -p "$LAMBDA_BUILD_DIR"

if [ ! -f "$LAMBDA_SRC_DIR/handler.py" ]; then
  echo "Error: Lambda handler not found at $LAMBDA_SRC_DIR/handler.py"
  exit 1
fi

cp "$LAMBDA_SRC_DIR/handler.py" "$LAMBDA_BUILD_DIR/handler.py"

if [ -f "$LAMBDA_SRC_DIR/requirements.txt" ]; then
  # Build Lambda dependencies in an Amazon Linux runtime container so compiled wheels
  # are compatible with Lambda (avoids platform-specific failures from local installs).
  MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*" docker run --rm \
    --entrypoint /bin/bash \
    -v "$LAMBDA_SRC_DIR":/src \
    -v "$LAMBDA_BUILD_DIR":/asset \
    public.ecr.aws/lambda/python:3.12 \
    -lc "python -m pip install -r /src/requirements.txt -t /asset --no-cache-dir >/dev/null"
fi

rm -f "$LAMBDA_ZIP_PATH"
(
  cd "$LAMBDA_BUILD_DIR"
  "$PYTHON_BIN" - <<'PY'
import os
import zipfile

zip_path = os.path.abspath(os.path.join(os.getcwd(), "..", "prescription_pdf_lambda.zip"))
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, _, files in os.walk("."):
        for name in files:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, ".")
            zf.write(full, rel)
print(zip_path)
PY
)

terraform_vars+=("-var=prescription_pdf_lambda_zip_path=${LAMBDA_ZIP_PATH}")

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

if command -v git >/dev/null 2>&1; then
  GIT_SHA="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || true)"
else
  GIT_SHA=""
fi

if [ -n "${GIT_SHA:-}" ]; then
  DEFAULT_DEPLOY_IMAGE_TAG="$(date -u +%Y%m%d%H%M%S)-${GIT_SHA}"
else
  DEFAULT_DEPLOY_IMAGE_TAG="$(date -u +%Y%m%d%H%M%S)"
fi

DEPLOY_IMAGE_TAG="${DEPLOY_IMAGE_TAG:-$DEFAULT_DEPLOY_IMAGE_TAG}"
DEPLOY_IMAGE_URI="${ECR_URL}:${DEPLOY_IMAGE_TAG}"

echo "Using image tag: ${DEPLOY_IMAGE_TAG}"
docker tag seva-arogya-backend:latest "$DEPLOY_IMAGE_URI"
docker push "$DEPLOY_IMAGE_URI"

echo ""
echo "==> Terraform apply (update ECS task definition)"
pushd "$INFRA_DIR" >/dev/null
terraform apply \
  "${terraform_vars[@]}" \
  -var="container_image=${DEPLOY_IMAGE_URI}" \
  -auto-approve
popd >/dev/null

echo ""
echo "==> Force ECS deployment"
aws ecs update-service \
  --cluster "$CLUSTER_NAME" \
  --service "$SERVICE_NAME" \
  --force-new-deployment \
  --region "$AWS_REGION" >/dev/null

echo "==> Waiting for ECS service to become stable"
ECS_STABLE_TIMEOUT_SECONDS="${ECS_STABLE_TIMEOUT_SECONDS:-900}"
ECS_WAIT_POLL_SECONDS="${ECS_WAIT_POLL_SECONDS:-15}"
WAIT_DEADLINE=$(( $(date +%s) + ECS_STABLE_TIMEOUT_SECONDS ))
LAST_EVENT=""

while true; do
  IS_STABLE="$(aws ecs describe-services \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME" \
    --region "$AWS_REGION" \
    --query 'length(services[0].deployments)==`1` && services[0].runningCount==services[0].desiredCount' \
    --output text)"

  COUNTS="$(aws ecs describe-services \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME" \
    --region "$AWS_REGION" \
    --query 'services[0].[desiredCount,runningCount,pendingCount]' \
    --output text)"
  DESIRED_COUNT="$(echo "$COUNTS" | awk '{print $1}')"
  RUNNING_COUNT="$(echo "$COUNTS" | awk '{print $2}')"
  PENDING_COUNT="$(echo "$COUNTS" | awk '{print $3}')"
  echo "ECS status: desired=${DESIRED_COUNT} running=${RUNNING_COUNT} pending=${PENDING_COUNT}"

  LATEST_EVENT="$(aws ecs describe-services \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME" \
    --region "$AWS_REGION" \
    --query 'services[0].events[0].message' \
    --output text 2>/dev/null || true)"
  if [ -n "$LATEST_EVENT" ] && [ "$LATEST_EVENT" != "None" ] && [ "$LATEST_EVENT" != "$LAST_EVENT" ]; then
    echo "Latest ECS event: $LATEST_EVENT"
    LAST_EVENT="$LATEST_EVENT"
  fi

  if [ "$IS_STABLE" = "True" ]; then
    break
  fi

  if [ "$(date +%s)" -ge "$WAIT_DEADLINE" ]; then
    echo "Error: ECS service did not stabilize within ${ECS_STABLE_TIMEOUT_SECONDS}s"
    echo "Recent ECS events:"
    aws ecs describe-services \
      --cluster "$CLUSTER_NAME" \
      --services "$SERVICE_NAME" \
      --region "$AWS_REGION" \
      --query 'services[0].events[0:10].[createdAt,message]' \
      --output table || true
    exit 1
  fi

  sleep "$ECS_WAIT_POLL_SECONDS"
done

echo ""
echo "Deployment complete."
echo "API Base URL: $ALB_URL"
echo "Liveness check: ${ALB_URL}/health/live"
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
