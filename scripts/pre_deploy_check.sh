#!/bin/bash

set -euo pipefail

# Pre-Deployment Check Script
# Validates AWS connectivity from local machine before deploying

echo "========================================="
echo "SEVA Arogya - Pre-Deployment Check"
echo "========================================="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: $ENV_FILE not found"
  exit 1
fi

# Load env
set -a
source "$ENV_FILE"
set +a

echo "Region: $AWS_REGION"
echo ""

# Check if Python is available
if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  echo "Error: Python is not installed"
  exit 1
fi

PYTHON_CMD="python3"
if ! command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python"
fi

echo "==> Running AWS connectivity tests..."
echo ""

# Run the connectivity test
cd "$ROOT_DIR"
if ! $PYTHON_CMD test_aws_connectivity.py; then
  echo ""
  echo "❌ Pre-deployment checks failed!"
  echo ""
  echo "AWS connectivity issues detected. Please fix these before deploying:"
  echo "  1. Check your internet connection"
  echo "  2. Verify AWS credentials in .env file"
  echo "  3. Ensure firewall/VPN is not blocking AWS endpoints"
  echo "  4. Test with: aws cognito-idp list-user-pools --max-results 1 --region $AWS_REGION"
  echo ""
  exit 1
fi

echo ""
echo "========================================="
echo "✓ Pre-Deployment Checks Passed"
echo "========================================="
echo ""
echo "Your local environment can connect to AWS services."
echo "You can proceed with deployment."
echo ""

exit 0
