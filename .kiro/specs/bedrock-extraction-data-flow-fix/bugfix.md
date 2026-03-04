# Bugfix Requirements Document

## Introduction

The medical extraction feature fails when attempting to invoke AWS Bedrock models for prescription data generation. The extraction API endpoint `/api/v1/extract` returns a 500 Internal Server Error, preventing the system from generating structured prescription data from medical consultation transcripts. The browser console shows the error: "POST https://sevaarogya.shoppertrends.in/api/v1/extract 500 (Internal Server Error)".

Investigation reveals that the IAM policy file `seva-arogya-infra/iam_policies/bedrock_comprehend_policy.json` contains incorrect action namespaces. The policy uses `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream`, but the boto3 bedrock-runtime client requires `bedrock-runtime:InvokeModel` and `bedrock-runtime:InvokeModelWithResponseStream`. This causes AccessDeniedException when the extraction pipeline attempts to invoke Bedrock models.

Additionally, the fix requires deployment verification through automated ECS testing integrated into the Terraform deployment process to ensure the pipeline works end-to-end after infrastructure changes.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the extraction API endpoint `/api/v1/extract` receives a POST request with transcript data THEN the system returns 500 Internal Server Error and fails to extract prescription data

1.2 WHEN the extraction pipeline calls `bedrock_client.generate_prescription_data()` with a transcript THEN the system raises AccessDeniedException due to missing `bedrock-runtime:InvokeModel` permission

1.3 WHEN the Bedrock client invokes `client.invoke_model()` using the boto3 bedrock-runtime client THEN AWS IAM denies the request because the ECS task role policy grants `bedrock:InvokeModel` instead of `bedrock-runtime:InvokeModel`

1.4 WHEN the IAM policy uses action `bedrock:InvokeModel` THEN the permission does not match the actual service namespace `bedrock-runtime` required by the boto3 client

1.5 WHEN Terraform deploys infrastructure changes THEN there is no automated test to verify the extraction pipeline works on ECS

### Expected Behavior (Correct)

2.1 WHEN the extraction API endpoint `/api/v1/extract` receives a POST request with transcript data THEN the system SHALL successfully extract prescription data and return 200 status with structured prescription data

2.2 WHEN the extraction pipeline calls `bedrock_client.generate_prescription_data()` with a transcript THEN the system SHALL successfully invoke the Bedrock model and return structured prescription data without AccessDeniedException

2.3 WHEN the Bedrock client invokes `client.invoke_model()` using the boto3 bedrock-runtime client THEN AWS IAM SHALL authorize the request because the ECS task role policy grants `bedrock-runtime:InvokeModel`

2.4 WHEN the IAM policy uses action `bedrock-runtime:InvokeModel` THEN the permission SHALL match the actual service namespace `bedrock-runtime` used by the boto3 client

2.5 WHEN Terraform deploys infrastructure changes THEN an automated ECS test SHALL verify the extraction pipeline works end-to-end (transcription → extraction → response)

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the extraction pipeline calls Comprehend Medical operations THEN the system SHALL CONTINUE TO successfully extract medical entities using the existing `comprehendmedical:*` permissions

3.2 WHEN the IAM policy specifies Bedrock model resource ARNs (e.g., `arn:aws:bedrock:*::foundation-model/anthropic.claude-3-*`) THEN the system SHALL CONTINUE TO restrict access to only the specified Claude 3 models

3.3 WHEN the Bedrock client uses `InvokeModelWithResponseStream` for streaming responses THEN the system SHALL CONTINUE TO have permission via `bedrock-runtime:InvokeModelWithResponseStream` (after namespace correction)

3.4 WHEN the extraction pipeline processes transcripts with valid medical entities THEN the system SHALL CONTINUE TO generate prescription data with the same structure and validation logic

3.5 WHEN the Bedrock client encounters rate limits or service unavailability THEN the system SHALL CONTINUE TO retry with exponential backoff as implemented in `_call_with_retry()`

3.6 WHEN transcription is completed THEN the system SHALL CONTINUE TO generate transcript text successfully as it does currently
