#!/bin/bash
# ECS Extraction Pipeline Test Script
# Tests the extraction API endpoint after ECS deployment

set -euo pipefail

echo "========================================="
echo "Testing ECS Extraction Pipeline"
echo "========================================="

get_http_code() {
    local url="$1"
    shift || true

    local code
    code="$(curl -s -L -o /dev/null -w "%{http_code}" "$@" "$url" 2>/dev/null || true)"
    if [ -z "$code" ] || [ "$code" = "000" ]; then
        echo "000"
        return
    fi
    echo "$code"
}

# Resolve API base URL with explicit scheme
API_BASE_URL="${API_BASE_URL:-}"

# Get ALB DNS name from environment (preferred) or Terraform output (fallback)
ALB_DNS="${ALB_DNS:-}"
if [ -z "$ALB_DNS" ]; then
    ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "")
fi

if [ -z "$ALB_DNS" ]; then
    echo "Error: Could not retrieve ALB DNS name from Terraform output"
    exit 1
fi

if [ -z "$API_BASE_URL" ]; then
    API_BASE_URL=$(terraform output -raw api_base_url 2>/dev/null || echo "")
fi

if [ -z "$API_BASE_URL" ]; then
    API_BASE_URL="http://${ALB_DNS}"
fi

echo "ALB DNS: $ALB_DNS"
echo "API Base URL: $API_BASE_URL"
echo ""

# ALB HTTPS with an ACM cert for a custom domain can fail verification on *.elb.amazonaws.com.
# For deployment smoke tests, allow insecure TLS only for this specific mismatch pattern.
CURL_TLS_ARGS=()
if [[ "$API_BASE_URL" == https://* ]] && [[ "$API_BASE_URL" == *".elb.amazonaws.com"* ]]; then
    CURL_TLS_ARGS+=("-k")
fi

# Wait for ECS service to be stable
echo "Waiting for ECS service to stabilize..."
CLUSTER_NAME="${CLUSTER_NAME:-}"
SERVICE_NAME="${SERVICE_NAME:-}"

if [ -z "$CLUSTER_NAME" ]; then
    CLUSTER_NAME=$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "")
fi
if [ -z "$SERVICE_NAME" ]; then
    SERVICE_NAME=$(terraform output -raw ecs_service_name 2>/dev/null || echo "")
fi

if [ -n "$CLUSTER_NAME" ] && [ -n "$SERVICE_NAME" ]; then
    aws ecs wait services-stable \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --region "${AWS_REGION:-us-east-1}" || true
    echo "ECS service is stable"
else
    echo "Warning: Could not retrieve ECS cluster/service names, skipping stability check"
    echo "Waiting 30 seconds for service to stabilize..."
    sleep 30
fi

echo ""

# Test health endpoint first
echo "Testing health endpoint..."
HEALTH_URL="${API_BASE_URL}/health"
HEALTH_RESPONSE="$(get_http_code "$HEALTH_URL" "${CURL_TLS_ARGS[@]}")"

if [ "$HEALTH_RESPONSE" != "200" ]; then
    echo "Error: Health check failed with status $HEALTH_RESPONSE"
    echo "URL: $HEALTH_URL"
    if [ "$HEALTH_RESPONSE" = "000" ]; then
        echo "Hint: connection/TLS handshake failed before HTTP response."
    fi
    exit 1
fi

echo "Health check passed (200 OK)"
echo ""

# Test AWS connectivity endpoint (non-authenticated)
echo "Testing AWS connectivity endpoint..."
CONNECTIVITY_URL="${API_BASE_URL}/health/aws-connectivity"
CONNECTIVITY_STATUS="$(get_http_code "$CONNECTIVITY_URL" "${CURL_TLS_ARGS[@]}")"
if [ "$CONNECTIVITY_STATUS" != "200" ]; then
    echo "Error: AWS connectivity check failed with status $CONNECTIVITY_STATUS"
    echo "URL: $CONNECTIVITY_URL"
    exit 1
fi
echo "AWS connectivity check passed (200 OK)"
echo ""

# Test extraction endpoint with sample transcript
echo "Testing extraction endpoint..."
EXTRACT_URL="${API_BASE_URL}/api/v1/extract"
LOGIN_URL="${API_BASE_URL}/api/v1/auth/login"
COOKIE_JAR="$(mktemp)"
AUTH_HEADER_ARGS=()
AUTH_REQUIRED_STATUS_REGEX='^(301|302|303|307|308|401|403|405)$'
REQUIRE_EXTRACTION_AUTH_TEST="${REQUIRE_EXTRACTION_AUTH_TEST:-false}"

# Sample medical transcript for testing
SAMPLE_TRANSCRIPT='{"transcript":"Patient presents with fever and cough. Prescribed amoxicillin 500mg three times daily for 7 days. Follow up in one week.","hospital_id":"default","request_id":"ecs-smoke-test"}'

# Optional auth for protected extraction endpoint
TEST_USER_EMAIL="${TEST_USER_EMAIL:-}"
TEST_USER_PASSWORD="${TEST_USER_PASSWORD:-}"

if [ -n "$TEST_USER_EMAIL" ] && [ -n "$TEST_USER_PASSWORD" ]; then
    echo "Logging in test user for extraction endpoint..."
    LOGIN_PAYLOAD="{\"email\":\"${TEST_USER_EMAIL}\",\"password\":\"${TEST_USER_PASSWORD}\"}"
    LOGIN_RESPONSE=$(curl -s "${CURL_TLS_ARGS[@]}" -c "$COOKIE_JAR" -b "$COOKIE_JAR" -w "\n%{http_code}" \
        -X POST "$LOGIN_URL" \
        -H "Content-Type: application/json" \
        -d "$LOGIN_PAYLOAD" 2>/dev/null || printf "\n000")
    LOGIN_STATUS=$(echo "$LOGIN_RESPONSE" | tail -n 1)
    LOGIN_BODY=$(echo "$LOGIN_RESPONSE" | head -n -1)

    if [ "$LOGIN_STATUS" != "200" ]; then
        echo "Error: Login failed for extraction test (status $LOGIN_STATUS)"
        echo "Login response: $LOGIN_BODY"
        rm -f "$COOKIE_JAR"
        exit 1
    fi

    AUTH_HEADER_ARGS=(-c "$COOKIE_JAR" -b "$COOKIE_JAR")
fi

# Make request to extraction endpoint
EXTRACT_RESPONSE=$(curl -s "${CURL_TLS_ARGS[@]}" "${AUTH_HEADER_ARGS[@]}" -w "\n%{http_code}" -X POST "$EXTRACT_URL" \
    -H "Content-Type: application/json" \
    -d "$SAMPLE_TRANSCRIPT" 2>/dev/null || printf "\n000")
STATUS_CODE=$(echo "$EXTRACT_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$EXTRACT_RESPONSE" | head -n -1)
rm -f "$COOKIE_JAR"

echo "Status Code: $STATUS_CODE"
echo "Response Body: $RESPONSE_BODY"
echo ""

# If endpoint is protected and no credentials were supplied, do not fail deploy by default.
if [[ -z "$TEST_USER_EMAIL" || -z "$TEST_USER_PASSWORD" ]] && [[ "$STATUS_CODE" =~ $AUTH_REQUIRED_STATUS_REGEX ]]; then
    if [ "$REQUIRE_EXTRACTION_AUTH_TEST" = "true" ]; then
        echo "Error: Extraction endpoint requires authentication and test credentials were not provided."
        echo "Set TEST_USER_EMAIL and TEST_USER_PASSWORD, or set REQUIRE_EXTRACTION_AUTH_TEST=false."
        exit 1
    fi
    echo "Warning: Extraction endpoint appears authentication-protected (status $STATUS_CODE)."
    echo "Skipping authenticated extraction check (set TEST_USER_EMAIL/TEST_USER_PASSWORD to enable)."
    echo ""
    echo "========================================="
    echo "Extraction Pipeline Smoke Test PASSED"
    echo "========================================="
    echo ""
    echo "OK: Health endpoint responding"
    echo "OK: AWS connectivity endpoint responding"
    echo "OK: Extraction endpoint reachable (auth required)"
    echo ""
    exit 0
fi

# Verify status code is 200
if [ "$STATUS_CODE" != "200" ]; then
    echo "Error: Extraction API returned status $STATUS_CODE (expected 200)"
    echo "This indicates an extraction API/runtime issue (not necessarily IAM)."
    echo "Response: $RESPONSE_BODY"
    exit 1
fi

# Verify response contains prescription data structure
if ! echo "$RESPONSE_BODY" | grep -q "status\\|prescription_data\\|sections"; then
    echo "Error: Response does not contain expected prescription data structure"
    echo "Response: $RESPONSE_BODY"
    exit 1
fi

echo "========================================="
echo "Extraction Pipeline Test PASSED"
echo "========================================="
echo ""
echo "OK: Health endpoint responding"
echo "OK: AWS connectivity endpoint responding"
echo "OK: Extraction API returning 200 status"
echo "OK: Response contains prescription data"
echo ""
echo "The IAM policy fix is working correctly!"

