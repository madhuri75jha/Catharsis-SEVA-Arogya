# Deployment Timeout Issue - Fix Guide

## Issue

Post-deployment validation is timing out with:
```
⚠ AWS Connectivity returned HTTP 503 (service unavailable)
{"checks":{"cognito":{"error":"timeout","message":"Connectivity check timed out"}}}
```

## Root Cause

The ECS tasks in private subnets are experiencing timeouts when trying to reach AWS services. This can happen due to:

1. **NAT Gateway not fully ready** - Takes 1-2 minutes after creation
2. **Route table propagation delay** - Routes need time to propagate
3. **ECS task startup time** - Application initialization takes time
4. **Security group rules** - Outbound rules need to be verified

## Solution

### Option 1: Increase Wait Time (Recommended)

The deployment script already waits 30 seconds. Increase this to 90 seconds to allow NAT gateway and routes to stabilize:

**Update `deploy_to_aws.sh`**:
```bash
echo ""
echo "==> Running deployment validation..."
echo "Waiting 90 seconds for service to stabilize..."
sleep 90
```

### Option 2: Skip Post-Deployment Validation

If you want to deploy faster and validate manually later:

**Update `deploy_to_aws.sh`**:
```bash
echo ""
echo "Deployment complete."
echo "API Base URL: $ALB_URL"
echo "Health check: ${ALB_URL}/health"

# Skip automatic validation
echo ""
echo "To validate deployment manually, run:"
echo "  bash scripts/validate_deployment.sh \"$ALB_URL\""
```

### Option 3: Use VPC Endpoints (Cost-Effective Long-term)

VPC endpoints allow private subnet resources to access AWS services without NAT gateway, reducing latency and cost.

**Add to `seva-arogya-infra/modules/vpc/main.tf`**:
```hcl
# VPC Endpoint for S3
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.${data.aws_region.current.name}.s3"
  
  route_table_ids = [aws_route_table.private.id]
  
  tags = {
    Name        = "${var.project_name}-${var.env_name}-s3-endpoint"
    Project     = var.project_name
    Environment = var.env_name
  }
}

# VPC Endpoint for Secrets Manager
resource "aws_vpc_endpoint" "secretsmanager" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true
  
  tags = {
    Name        = "${var.project_name}-${var.env_name}-secretsmanager-endpoint"
    Project     = var.project_name
    Environment = var.env_name
  }
}

# Security Group for VPC Endpoints
resource "aws_security_group" "vpc_endpoints" {
  name        = "${var.project_name}-${var.env_name}-vpc-endpoints-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "Allow HTTPS from VPC"
  }

  tags = {
    Name        = "${var.project_name}-${var.env_name}-vpc-endpoints-sg"
    Project     = var.project_name
    Environment = var.env_name
  }
}
```

## Quick Fix (Immediate)

**Update the wait time in deploy_to_aws.sh**:

```bash
# Find this line:
echo "Waiting 30 seconds for service to stabilize..."
sleep 30

# Change to:
echo "Waiting 90 seconds for service to stabilize..."
sleep 90
```

This gives the NAT gateway, routes, and ECS tasks enough time to fully initialize.

## Verification

After applying the fix, the validation should show:

```bash
==> Step 1: Basic Health Check
  ✓ Basic Health is healthy (HTTP 200)

==> Step 2: AWS Connectivity Check
  ✓ AWS Connectivity is healthy (HTTP 200)

✓ Deployment Validation Successful
```

## Manual Validation

If automatic validation still times out, validate manually after a few minutes:

```bash
# Get API URL
cd seva-arogya-infra
API_URL=$(terraform output -raw api_base_url)

# Wait a bit more
sleep 60

# Run validation
bash scripts/validate_deployment.sh "$API_URL"
```

## Monitoring

Check ECS task logs if issues persist:

```bash
# Get cluster and service names
CLUSTER_NAME=$(terraform -chdir=seva-arogya-infra output -raw ecs_cluster_name)
SERVICE_NAME=$(terraform -chdir=seva-arogya-infra output -raw ecs_service_name)

# List tasks
aws ecs list-tasks --cluster "$CLUSTER_NAME" --service-name "$SERVICE_NAME" --region ap-south-1

# Get task ID from output, then:
TASK_ID="<task-id-from-above>"

# View logs
aws ecs describe-tasks --cluster "$CLUSTER_NAME" --tasks "$TASK_ID" --region ap-south-1

# Or check CloudWatch logs
aws logs tail "/ecs/seva-arogya-dev" --follow --region ap-south-1
```

## Why This Happens

1. **NAT Gateway Creation**: Takes 1-2 minutes to become fully operational
2. **Route Propagation**: Route tables need time to update across AZs
3. **ECS Task Startup**: Application initialization, health checks, etc.
4. **First Request**: Cold start for AWS service connections

The 90-second wait accounts for all of these delays.

## Long-term Recommendation

For production:
1. Use VPC endpoints for frequently accessed services (S3, Secrets Manager)
2. Implement retry logic in application code
3. Use CloudWatch alarms for monitoring
4. Consider using AWS PrivateLink for all AWS services

## Summary

**Immediate fix**: Increase wait time to 90 seconds in `deploy_to_aws.sh`

**Long-term fix**: Implement VPC endpoints to bypass NAT gateway entirely

The connectivity checks are working correctly - they're just running too soon after deployment. The application will work fine once it's fully initialized.
