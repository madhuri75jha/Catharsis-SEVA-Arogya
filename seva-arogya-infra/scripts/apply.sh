#!/bin/bash
# Terraform Apply Script

set -e

echo "========================================="
echo "Applying Terraform Configuration"
echo "========================================="

# Check if plan file exists
if [ ! -f tfplan ]; then
    echo "Error: tfplan file not found"
    echo "Please run ./scripts/plan.sh first"
    exit 1
fi

# Apply the plan
echo ""
echo "Running terraform apply..."
terraform apply tfplan

# Remove plan file after successful apply
rm -f tfplan

echo ""
echo "========================================="
echo "Infrastructure deployed successfully!"
echo "========================================="
echo ""
echo "Important outputs:"
terraform output

echo ""
echo "Next steps:"
echo "  1. Build and push Docker image to ECR"
echo "  2. Update ECS service to deploy the image"
echo "  3. Deploy frontend to S3"
echo "  4. Invalidate CloudFront cache (if enabled)"
echo ""
echo "See README.md for detailed deployment instructions"
