# Bedrock Medical Extraction - IAM Setup

## Overview

This document describes the IAM permissions required for the Bedrock Medical Extraction feature.

## Required AWS Services

1. **AWS Comprehend Medical** - For medical entity extraction
2. **AWS Bedrock** - For AI-powered prescription data extraction using Claude 3 models

## IAM Policy

The IAM policy for ECS task execution is defined in `iam_policies/bedrock_comprehend_policy.json`.

### Permissions Breakdown

#### Comprehend Medical Permissions
- `comprehendmedical:DetectEntitiesV2` - Extract medical entities from text
- `comprehendmedical:InferICD10CM` - (Optional) Infer ICD-10-CM codes
- `comprehendmedical:InferRxNorm` - (Optional) Infer RxNorm codes

#### Bedrock Permissions
- `bedrock:InvokeModel` - Invoke Bedrock foundation models
- `bedrock:InvokeModelWithResponseStream` - (Optional) Stream responses

### Supported Models

The policy grants access to Claude 3 family models:
- `anthropic.claude-3-sonnet-20240229-v1:0` (Recommended - default)
- `anthropic.claude-3-opus-20240229-v1:0` (Most capable)
- `anthropic.claude-3-haiku-20240307-v1:0` (Fastest)
- `anthropic.claude-3-5-sonnet-20240620-v1:0` (Latest)

## Terraform Integration

### Adding to ECS Task Role

Add the policy to your ECS task role in `seva-arogya-infra/modules/ecs/main.tf`:

```hcl
# Add Bedrock and Comprehend Medical permissions
resource "aws_iam_role_policy" "bedrock_comprehend" {
  name   = "${var.project_name}-${var.env_name}-bedrock-comprehend"
  role   = aws_iam_role.ecs_task_role.id
  policy = file("${path.module}/../../iam_policies/bedrock_comprehend_policy.json")
}
```

### Environment Variables

Add to your ECS task definition environment variables:

```hcl
environment = [
  # ... existing variables ...
  {
    name  = "BEDROCK_REGION"
    value = var.bedrock_region
  },
  {
    name  = "BEDROCK_MODEL_ID"
    value = var.bedrock_model_id
  }
]
```

### Variables

Add to `seva-arogya-infra/variables.tf`:

```hcl
variable "bedrock_region" {
  description = "AWS region for Bedrock service"
  type        = string
  default     = "us-east-1"  # Bedrock is available in limited regions
}

variable "bedrock_model_id" {
  description = "Bedrock model ID for medical extraction"
  type        = string
  default     = "anthropic.claude-3-sonnet-20240229-v1:0"
}
```

## Regional Availability

### Comprehend Medical
Available in: us-east-1, us-east-2, us-west-2, ap-southeast-2, ca-central-1, eu-west-1, eu-west-2

### Bedrock (Claude 3)
Available in: us-east-1, us-west-2, ap-southeast-1, ap-northeast-1, eu-central-1, eu-west-3

**Note:** If your primary region (ap-south-1) doesn't support these services, configure cross-region access:
- Set `AWS_COMPREHEND_REGION=us-east-1` in environment
- Set `BEDROCK_REGION=us-east-1` in environment

## Cost Considerations

### Comprehend Medical Pricing (us-east-1)
- DetectEntitiesV2: $0.01 per 100 characters (minimum 300 characters)
- Typical transcript (1000 chars): ~$0.10

### Bedrock Pricing (Claude 3 Sonnet)
- Input: $0.003 per 1K tokens (~750 words)
- Output: $0.015 per 1K tokens
- Typical extraction: ~$0.05-0.10 per prescription

**Estimated cost per prescription extraction: $0.15-0.20**

## Security Best Practices

1. **Least Privilege**: The policy only grants access to specific Bedrock models
2. **Resource Restrictions**: Comprehend Medical actions are scoped to necessary operations
3. **No Data Logging**: Ensure CloudWatch logs don't capture PHI from transcripts
4. **Encryption**: All data in transit uses TLS 1.2+
5. **IAM Roles**: Use ECS task roles, not access keys

## Testing IAM Permissions

Test the permissions locally:

```bash
# Test Comprehend Medical access
aws comprehendmedical detect-entities-v2 \
  --text "Patient has fever and cough" \
  --region us-east-1

# Test Bedrock access
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-3-sonnet-20240229-v1:0 \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":100,"messages":[{"role":"user","content":"Hello"}]}' \
  --region us-east-1 \
  output.json
```

## Troubleshooting

### Access Denied Errors

1. **Check IAM role attachment**: Ensure the policy is attached to the ECS task role
2. **Verify region**: Bedrock/Comprehend must be called in supported regions
3. **Model access**: Some Bedrock models require explicit access request in AWS Console
4. **Service quotas**: Check AWS Service Quotas for Bedrock invocations

### Model Access Request

If you get "Access Denied" for Bedrock models:
1. Go to AWS Console → Bedrock → Model access
2. Request access to Claude 3 models
3. Wait for approval (usually instant for Claude 3)

## Deployment Checklist

- [ ] Add IAM policy to ECS task role
- [ ] Set BEDROCK_REGION environment variable
- [ ] Set BEDROCK_MODEL_ID environment variable  
- [ ] Request Bedrock model access in AWS Console
- [ ] Test Comprehend Medical access
- [ ] Test Bedrock access
- [ ] Verify hospital configuration files exist in /config/hospitals/
- [ ] Monitor CloudWatch logs for PHI leakage
- [ ] Set up cost alerts for Bedrock/Comprehend usage
