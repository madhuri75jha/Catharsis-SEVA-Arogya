# Bugfix Requirements Document

## Introduction

The medical extraction feature fails when attempting to invoke AWS Bedrock models for prescription data generation. The ECS task role (arn:aws:sts::556731123813:assumed-role/seva-arogya-dev-ecs-task-role) lacks the required IAM permission `bedrock-runtime:InvokeModel`, causing an AccessDeniedException during the extraction pipeline execution. This prevents the system from generating structured prescription data from medical consultation transcripts.

The IAM policy file `seva-arogya-infra/iam_policies/bedrock_comprehend_policy.json` contains the correct permissions but uses the incorrect action namespace `bedrock:InvokeModel` instead of `bedrock-runtime:InvokeModel`. The Bedrock Runtime service requires the `bedrock-runtime` namespace for model invocation operations.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the extraction pipeline calls `bedrock_client.generate_prescription_data()` with a transcript THEN the system raises AccessDeniedException with error code indicating missing `bedrock-runtime:InvokeModel` permission

1.2 WHEN the Bedrock client invokes `client.invoke_model()` using the boto3 bedrock-runtime client THEN the AWS IAM service denies the request because the ECS task role policy grants `bedrock:InvokeModel` instead of `bedrock-runtime:InvokeModel`

1.3 WHEN the IAM policy uses action `bedrock:InvokeModel` THEN the permission does not match the actual service namespace `bedrock-runtime` used by the boto3 client

### Expected Behavior (Correct)

2.1 WHEN the extraction pipeline calls `bedrock_client.generate_prescription_data()` with a transcript THEN the system SHALL successfully invoke the Bedrock model and return structured prescription data without AccessDeniedException

2.2 WHEN the Bedrock client invokes `client.invoke_model()` using the boto3 bedrock-runtime client THEN the AWS IAM service SHALL authorize the request because the ECS task role policy grants `bedrock-runtime:InvokeModel`

2.3 WHEN the IAM policy uses action `bedrock-runtime:InvokeModel` THEN the permission SHALL match the actual service namespace `bedrock-runtime` used by the boto3 client and allow model invocation

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the extraction pipeline calls Comprehend Medical operations THEN the system SHALL CONTINUE TO successfully extract medical entities using the existing `comprehendmedical:*` permissions

3.2 WHEN the IAM policy specifies Bedrock model resource ARNs (e.g., `arn:aws:bedrock:*::foundation-model/anthropic.claude-3-*`) THEN the system SHALL CONTINUE TO restrict access to only the specified Claude 3 models

3.3 WHEN the Bedrock client uses `InvokeModelWithResponseStream` for streaming responses THEN the system SHALL CONTINUE TO have permission via `bedrock-runtime:InvokeModelWithResponseStream` (after namespace correction)

3.4 WHEN the extraction pipeline processes transcripts with valid medical entities THEN the system SHALL CONTINUE TO generate prescription data with the same structure and validation logic

3.5 WHEN the Bedrock client encounters rate limits or service unavailability THEN the system SHALL CONTINUE TO retry with exponential backoff as implemented in `_call_with_retry()`
