# Terraform Updates for Prescription Enhancement Feature

## Overview

The prescription enhancement feature requires additional IAM permissions for CloudWatch Logs access and S3 operations. This document outlines the necessary Terraform changes.

## Required Changes

### 1. IAM Policy Updates

#### New Policy File Created

**File:** `seva-arogya-infra/iam_policies/prescription_enhancement_policy.json`

This policy grants:
- **CloudWatch Logs Read Access:** For the logs viewer feature (DeveloperAdmin only)
- **S3 PDF Bucket Access:** For PDF generation and storage
- **S3 Audio Bucket Delete Access:** For cleanup scheduler to remove expired audio files

#### Integration with Existing Infrastructure

The new policy needs to be attached to the ECS task execution role. Update your Terraform configuration to include this policy.

### 2. Terraform Configuration Updates

#### Option A: Update Existing IAM Role (Recommended)

If you have an existing ECS task role, add the new policy:

```hcl
# In your main.tf or iam.tf file

# Read the new policy file
data "aws_iam_policy_document" "prescription_enhancement" {
  source_policy_documents = [
    templatefile("${path.module}/iam_policies/prescription_enhancement_policy.json", {
      pdf_bucket_name   = var.s3_pdf_bucket_name
      audio_bucket_name = var.s3_audio_bucket_name
    })
  ]
}

# Create the policy
resource "aws_iam_policy" "prescription_enhancement" {
  name        = "${var.project_name}-${var.env_name}-prescription-enhancement"
  description = "Permissions for prescription enhancement features"
  policy      = data.aws_iam_policy_document.prescription_enhancement.json
}

# Attach to existing ECS task role
resource "aws_iam_role_policy_attachment" "ecs_task_prescription_enhancement" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.prescription_enhancement.arn
}
```

#### Option B: Inline Policy (Alternative)

If you prefer inline policies:

```hcl
resource "aws_iam_role_policy" "prescription_enhancement" {
  name = "prescription-enhancement"
  role = aws_iam_role.ecs_task_role.id

  policy = templatefile("${path.module}/iam_policies/prescription_enhancement_policy.json", {
    pdf_bucket_name   = var.s3_pdf_bucket_name
    audio_bucket_name = var.s3_audio_bucket_name
  })
}
```

### 3. Cognito User Pool Updates

The feature requires custom attributes in Cognito for role-based access control.

#### Add Custom Attributes

```hcl
resource "aws_cognito_user_pool" "main" {
  # ... existing configuration ...

  schema {
    name                = "role"
    attribute_data_type = "String"
    mutable             = true
    
    string_attribute_constraints {
      min_length = 1
      max_length = 50
    }
  }

  schema {
    name                = "hospital_id"
    attribute_data_type = "String"
    mutable             = true
    
    string_attribute_constraints {
      min_length = 1
      max_length = 100
    }
  }
}
```

**Note:** Custom attributes cannot be added to existing user pools. If your user pool already exists, you have two options:
1. Create a new user pool with custom attributes (requires user migration)
2. Store role information in a separate database table (already implemented via `user_roles` table)

**Recommendation:** Use the `user_roles` table approach (already implemented) to avoid user pool recreation.

### 4. Environment Variables

Ensure these environment variables are set in your ECS task definition:

```hcl
resource "aws_ecs_task_definition" "app" {
  # ... existing configuration ...

  container_definitions = jsonencode([{
    # ... existing container config ...
    
    environment = [
      # ... existing environment variables ...
      
      # Prescription Enhancement Variables
      {
        name  = "CLOUDWATCH_LOG_GROUP_NAME"
        value = "/aws/ecs/seva-arogya"
      },
      {
        name  = "AWS_CLOUDWATCH_REGION"
        value = var.aws_region
      },
      {
        name  = "CLEANUP_SCHEDULE_ENABLED"
        value = "true"
      },
      {
        name  = "CLEANUP_RETENTION_DAYS"
        value = "30"
      },
      {
        name  = "PDF_GENERATION_TIMEOUT"
        value = "30"
      },
      {
        name  = "PDF_MAX_FILE_SIZE_MB"
        value = "10"
      },
      {
        name  = "ENABLE_PRESCRIPTION_WORKFLOW"
        value = "true"
      },
      {
        name  = "ENABLE_CLOUDWATCH_LOGS_VIEWER"
        value = "true"
      }
    ]
  }])
}
```

### 5. S3 Bucket Configuration (If Not Already Exists)

Ensure you have a dedicated PDF bucket:

```hcl
resource "aws_s3_bucket" "pdf" {
  bucket = "${var.project_name}-${var.env_name}-pdf"
  
  tags = {
    Name        = "${var.project_name}-${var.env_name}-pdf"
    Environment = var.env_name
    Purpose     = "Prescription PDFs"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "pdf" {
  bucket = aws_s3_bucket.pdf.id

  rule {
    id     = "delete-old-pdfs"
    status = "Enabled"

    expiration {
      days = 90  # Adjust based on retention requirements
    }
  }
}

resource "aws_s3_bucket_versioning" "pdf" {
  bucket = aws_s3_bucket.pdf.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "pdf" {
  bucket = aws_s3_bucket.pdf.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

### 6. CloudWatch Log Group (If Not Already Exists)

Ensure the log group exists:

```hcl
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/aws/ecs/seva-arogya"
  retention_in_days = 30  # Adjust based on requirements

  tags = {
    Name        = "${var.project_name}-${var.env_name}-logs"
    Environment = var.env_name
  }
}
```

## Deployment Steps

### 1. Review Changes

```bash
cd seva-arogya-infra
terraform plan
```

### 2. Apply Changes

```bash
terraform apply
```

### 3. Verify Permissions

After applying, verify the ECS task role has the new permissions:

```bash
# Get the role ARN
aws iam list-attached-role-policies --role-name seva-arogya-dev-ecs-task-role

# Verify CloudWatch Logs access
aws logs describe-log-streams --log-group-name /aws/ecs/seva-arogya --limit 1

# Verify S3 PDF bucket access
aws s3 ls s3://seva-arogya-dev-pdf/
```

### 4. Update Application

After Terraform changes are applied:

1. Rebuild and push Docker image with new code
2. Update ECS service to use new task definition
3. Run database migrations
4. Verify application functionality

## Rollback Plan

If issues occur:

1. **Revert Terraform Changes:**
   ```bash
   terraform apply -target=aws_iam_policy.prescription_enhancement -destroy
   ```

2. **Revert Application:**
   - Deploy previous Docker image version
   - Restore database from backup if needed

3. **Disable Features:**
   - Set `ENABLE_PRESCRIPTION_WORKFLOW=false`
   - Set `ENABLE_CLOUDWATCH_LOGS_VIEWER=false`

## Validation Checklist

After deployment:

- [ ] ECS task role has new IAM policy attached
- [ ] CloudWatch Logs accessible from application
- [ ] PDF generation works and uploads to S3
- [ ] Cleanup scheduler can delete S3 objects
- [ ] CloudWatch logs viewer accessible (DeveloperAdmin)
- [ ] No permission errors in application logs
- [ ] All environment variables set correctly

## Cost Considerations

### New AWS Resources

1. **CloudWatch Logs API Calls:**
   - Estimated: $0.01 per 1,000 requests
   - Expected usage: ~100 requests/day (DeveloperAdmin only)
   - Monthly cost: ~$0.03

2. **S3 PDF Storage:**
   - Estimated: $0.023 per GB/month
   - Expected usage: ~10 GB/month (assuming 1,000 PDFs @ 10MB each)
   - Monthly cost: ~$0.23

3. **S3 API Calls:**
   - PUT requests: $0.005 per 1,000 requests
   - GET requests: $0.0004 per 1,000 requests
   - Expected usage: ~1,000 PUT + 5,000 GET per month
   - Monthly cost: ~$0.007

**Total Estimated Additional Cost:** ~$0.27/month

## Security Considerations

1. **Least Privilege:** IAM policy grants only necessary permissions
2. **Resource Restrictions:** CloudWatch Logs access limited to specific log group
3. **S3 Bucket Policies:** Consider adding bucket policies for additional security
4. **Encryption:** PDFs encrypted at rest using S3 server-side encryption
5. **Access Logging:** Enable S3 access logging for audit trail

## Monitoring

Set up CloudWatch alarms for:

1. **IAM Permission Errors:**
   ```hcl
   resource "aws_cloudwatch_metric_alarm" "iam_errors" {
     alarm_name          = "${var.project_name}-${var.env_name}-iam-errors"
     comparison_operator = "GreaterThanThreshold"
     evaluation_periods  = "1"
     metric_name         = "Errors"
     namespace           = "AWS/Logs"
     period              = "300"
     statistic           = "Sum"
     threshold           = "10"
     alarm_description   = "IAM permission errors detected"
   }
   ```

2. **S3 Upload Failures:**
   - Monitor application logs for S3 upload errors
   - Set up alerts for repeated failures

3. **PDF Generation Timeouts:**
   - Monitor PDF generation duration
   - Alert if exceeding threshold (30s)

## Support

For issues or questions:
- Review CloudWatch Logs: `/aws/ecs/seva-arogya`
- Check IAM permissions: AWS IAM Console
- Verify S3 bucket access: AWS S3 Console

## References

- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [CloudWatch Logs Permissions](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/permissions-reference-cwl.html)
- [S3 Bucket Policies](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html)
- [ECS Task IAM Roles](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)
