#!/bin/bash
# Terraform Initialization Script

set -e

echo "========================================="
echo "Initializing Terraform"
echo "========================================="

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo "Error: Terraform is not installed"
    echo "Please install Terraform >= 1.6 from https://www.terraform.io/downloads"
    exit 1
fi

# Check Terraform version
TERRAFORM_VERSION=$(terraform version -json | grep -o '"terraform_version":"[^"]*' | cut -d'"' -f4)
echo "Terraform version: $TERRAFORM_VERSION"

# Initialize Terraform
echo ""
echo "Running terraform init..."
terraform init

echo ""
echo "========================================="
echo "Terraform initialized successfully!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Configure your .env file at the repo root with required variables"
echo "  2. Run: ./scripts/plan.sh"
echo "  3. Review the plan"
echo "  4. Run: ./scripts/apply.sh"
