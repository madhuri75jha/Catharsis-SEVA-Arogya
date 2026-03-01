#!/bin/bash

set -euo pipefail

# Deployment Validation Script
# Runs connectivity tests after deployment to ensure all AWS services are accessible

echo "========================================="
echo "SEVA Arogya - Deployment Validation"
echo "========================================="

# Get the API base URL from command line or terraform output
API_BASE_URL="${1:-}"

if [ -z "$API_BASE_URL" ]; then
  echo "Attempting to get API URL from Terraform..."
  INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../seva-arogya-infra" && pwd)"

  if [ -d "$INFRA_DIR" ]; then
    pushd "$INFRA_DIR" >/dev/null
    API_BASE_URL="$(terraform output -raw api_base_url 2>/dev/null || echo "")"
    popd >/dev/null
  fi

  if [ -z "$API_BASE_URL" ]; then
    echo "Error: API_BASE_URL not provided and could not be retrieved from Terraform"
    echo "Usage: $0 <API_BASE_URL>"
    echo "Example: $0 http://seva-arogya-dev-alb-123456789.ap-south-1.elb.amazonaws.com"
    exit 1
  fi
fi

echo "API Base URL: $API_BASE_URL"
echo ""

# Last response details (updated by check_endpoint)
LAST_HTTP_CODE=""
LAST_BODY=""

# Function to check endpoint with retries
check_endpoint() {
  local url="$1"
  local name="$2"
  local max_retries="${3:-5}"
  local retry_delay="${4:-10}"

  echo "Checking $name..."

  # Determine if we need to skip SSL verification for HTTPS URLs
  local curl_opts="-s -w \n%{http_code}"
  if [[ "$url" == https://* ]]; then
    curl_opts="$curl_opts -k"
  fi

  for i in $(seq 1 $max_retries); do
    echo "  Attempt $i/$max_retries..."

    response=$(curl $curl_opts "$url" 2>/dev/null || echo "000")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    LAST_HTTP_CODE="$http_code"
    LAST_BODY="$body"

    if [ "$http_code" = "200" ]; then
      echo "  OK  $name is healthy (HTTP $http_code)"
      echo "  Response: $body" | head -c 200
      echo ""
      return 0
    elif [ "$http_code" = "503" ]; then
      echo "  WARN $name returned HTTP 503 (service unavailable)"
      echo "  Response: $body" | head -c 200
      echo ""

      if [ $i -lt $max_retries ]; then
        echo "  Retrying in ${retry_delay}s..."
        sleep $retry_delay
      fi
    else
      echo "  FAIL $name check failed (HTTP $http_code)"

      if [ $i -lt $max_retries ]; then
        echo "  Retrying in ${retry_delay}s..."
        sleep $retry_delay
      fi
    fi
  done

  echo "  FAIL $name check failed after $max_retries attempts"
  return 1
}

# Print detailed AWS connectivity breakdown from JSON response
print_aws_connectivity_details() {
  local body="$1"

  if [ -z "$body" ]; then
    echo "  No response body returned from /health/aws-connectivity."
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 - "$body" <<'PY'
import json, sys

body = sys.argv[1]
try:
    data = json.loads(body)
except Exception:
    print("  Response (raw): " + body[:500])
    raise SystemExit(0)

checks = data.get("checks", {})
if not isinstance(checks, dict) or not checks:
    print("  No per-service checks found in response.")
    raise SystemExit(0)

def format_line(name, info):
    status = info.get("status", "unknown")
    service = info.get("service") or name
    endpoint = info.get("endpoint")
    duration = info.get("duration_ms")
    msg = info.get("message") or info.get("error") or "no message"
    parts = [f"{name} ({service})", f"status={status}"]
    if endpoint:
        parts.append(f"endpoint={endpoint}")
    if duration is not None:
        parts.append(f"duration_ms={duration}")
    parts.append(f"message={msg}")
    return " | ".join(parts)

print("  Service breakdown:")
for name, info in checks.items():
    if not isinstance(info, dict):
        print(f"  UNKNOWN: {name} | status=unknown | message=invalid check payload")
        continue
    status = str(info.get("status", "unknown")).lower()
    if status in ("healthy", "ok"):
        label = "HEALTHY"
    elif status in ("skipped", "disabled"):
        label = "SKIPPED"
    else:
        label = "UNHEALTHY"
    print(f"  {label}: {format_line(name, info)}")
PY
  elif command -v python >/dev/null 2>&1; then
    python - "$body" <<'PY'
import json, sys
body = sys.argv[1]
try:
    data = json.loads(body)
except Exception:
    print("  Response (raw): " + body[:500])
    raise SystemExit(0)

checks = data.get("checks", {})
if not isinstance(checks, dict) or not checks:
    print("  No per-service checks found in response.")
    raise SystemExit(0)

def format_line(name, info):
    status = info.get("status", "unknown")
    service = info.get("service") or name
    endpoint = info.get("endpoint")
    duration = info.get("duration_ms")
    msg = info.get("message") or info.get("error") or "no message"
    parts = [f"{name} ({service})", f"status={status}"]
    if endpoint:
        parts.append(f"endpoint={endpoint}")
    if duration is not None:
        parts.append(f"duration_ms={duration}")
    parts.append(f"message={msg}")
    return " | ".join(parts)

print("  Service breakdown:")
for name, info in checks.items():
    if not isinstance(info, dict):
        print(f"  UNKNOWN: {name} | status=unknown | message=invalid check payload")
        continue
    status = str(info.get("status", "unknown")).lower()
    if status in ("healthy", "ok"):
        label = "HEALTHY"
    elif status in ("skipped", "disabled"):
        label = "SKIPPED"
    else:
        label = "UNHEALTHY"
    print(f"  {label}: {format_line(name, info)}")
PY
  else
    echo "  Python is not available; raw response:"
    echo "  $body" | head -c 500
    echo ""
  fi
}

# Check basic health endpoint
echo "==> Step 1: Basic Health Check"
if ! check_endpoint "${API_BASE_URL}/health" "Basic Health" 10 15; then
  echo ""
  echo "FAIL Basic health check failed. Deployment may have issues."
  echo "Check ECS task logs for errors."
  exit 1
fi

echo ""
echo "==> Step 2: AWS Connectivity Check"
if ! check_endpoint "${API_BASE_URL}/health/aws-connectivity" "AWS Connectivity" 5 10; then
  echo ""
  print_aws_connectivity_details "$LAST_BODY"
  echo ""
  echo "FAIL AWS connectivity check failed."
  echo "This indicates issues connecting to AWS services (Cognito, S3, Transcribe, etc.)"
  echo ""
  echo "Common causes:"
  echo "  1. Security group rules blocking outbound traffic"
  echo "  2. IAM role permissions missing"
  echo "  3. AWS service endpoints not accessible from VPC"
  echo "  4. Incorrect AWS credentials or region configuration"
  echo ""
  echo "To debug:"
  echo "  1. Check ECS task logs: aws ecs describe-tasks --cluster <cluster> --tasks <task-id>"
  echo "  2. Verify security group allows outbound HTTPS (443)"
  echo "  3. Check IAM task role has required permissions"
  echo "  4. Verify VPC has internet gateway or NAT gateway for private subnets"
  exit 1
fi

echo ""
print_aws_connectivity_details "$LAST_BODY"

echo ""
echo "========================================="
echo "OK Deployment Validation Successful"
echo "========================================="
echo ""
echo "All checks passed! Your deployment is healthy and ready to use."
echo ""
echo "Next steps:"

echo "  - Access the application: $API_BASE_URL"
echo "  - Test login functionality"
echo "  - Monitor CloudWatch logs for any issues"
echo ""

exit 0
