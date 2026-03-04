# Bedrock Extraction Data Flow Fix - Bugfix Design

## Overview

This bugfix addresses an IAM permission misconfiguration that prevents the medical extraction feature from invoking AWS Bedrock models. The root cause is an incorrect namespace in the IAM policy file: the policy grants `bedrock:InvokeModel` permissions, but the boto3 bedrock-runtime client requires `bedrock-runtime:InvokeModel`. This namespace mismatch causes AccessDeniedException errors when the extraction pipeline attempts to generate prescription data from medical transcripts.

The fix involves correcting the IAM policy namespace from `bedrock:` to `bedrock-runtime:` for model invocation actions, and adding automated ECS testing to the Terraform deployment process to verify the extraction pipeline works end-to-end after infrastructure changes.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when the extraction pipeline attempts to invoke Bedrock models using a boto3 bedrock-runtime client, but the IAM policy grants permissions using the incorrect `bedrock:` namespace instead of `bedrock-runtime:`
- **Property (P)**: The desired behavior when Bedrock model invocation is attempted - the IAM policy should authorize the request using the correct `bedrock-runtime:` namespace, allowing successful model invocation
- **Preservation**: Existing Comprehend Medical permissions, Bedrock model resource restrictions, streaming invocation permissions, retry logic, and transcription functionality that must remain unchanged by the fix
- **bedrock-runtime client**: The boto3 client used in `aws_services/bedrock_client.py` that requires `bedrock-runtime:` namespace permissions for `invoke_model()` and `invoke_model_with_response_stream()` operations
- **ECS task role**: The IAM role attached to ECS tasks that determines what AWS service actions the containerized application can perform
- **bedrock_comprehend_policy.json**: The IAM policy file in `seva-arogya-infra/iam_policies/` that defines permissions for the ECS task role

## Bug Details

### Fault Condition

The bug manifests when the extraction pipeline attempts to invoke AWS Bedrock models through the boto3 bedrock-runtime client. The IAM policy file uses the incorrect service namespace `bedrock:` for InvokeModel actions, but the boto3 bedrock-runtime client requires the `bedrock-runtime:` namespace. This namespace mismatch causes AWS IAM to deny the request with AccessDeniedException.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type BedrockInvocationRequest
  OUTPUT: boolean
  
  RETURN input.operation IN ['InvokeModel', 'InvokeModelWithResponseStream']
         AND input.client_type == 'bedrock-runtime'
         AND iamPolicyGrantsPermission('bedrock:' + input.operation)
         AND NOT iamPolicyGrantsPermission('bedrock-runtime:' + input.operation)
END FUNCTION
```

### Examples

- **Example 1**: User completes a medical consultation and clicks "Generate Prescription" → Frontend calls `/api/v1/extract` with transcript → Backend calls `bedrock_client.generate_prescription_data()` → boto3 bedrock-runtime client attempts `invoke_model()` → AWS IAM checks for `bedrock-runtime:InvokeModel` permission → Policy only grants `bedrock:InvokeModel` → AccessDeniedException raised → API returns 500 error
  - **Expected**: API returns 200 with structured prescription data
  - **Actual**: API returns 500 Internal Server Error

- **Example 2**: Extraction pipeline invokes Claude 3 Sonnet model with medical transcript → boto3 client calls `client.invoke_model(modelId='anthropic.claude-3-sonnet-20240229-v1:0')` → IAM evaluates request against policy actions → Finds `bedrock:InvokeModel` but needs `bedrock-runtime:InvokeModel` → Request denied
  - **Expected**: Model invocation succeeds and returns structured medical data
  - **Actual**: AccessDeniedException: User is not authorized to perform: bedrock-runtime:InvokeModel

- **Example 3**: Streaming response invocation attempts to use `invoke_model_with_response_stream()` → IAM policy grants `bedrock:InvokeModelWithResponseStream` → boto3 bedrock-runtime client requires `bedrock-runtime:InvokeModelWithResponseStream` → Permission denied
  - **Expected**: Streaming response works with correct namespace
  - **Actual**: AccessDeniedException for streaming operations

- **Edge Case**: Comprehend Medical operations (e.g., `detect_entities_v2()`) continue to work correctly because they use the `comprehendmedical:` namespace which is correctly specified in the policy
  - **Expected**: Comprehend Medical operations unaffected by Bedrock namespace fix
  - **Actual**: Comprehend Medical operations work correctly (preservation requirement)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Comprehend Medical operations must continue to work with existing `comprehendmedical:*` permissions
- Bedrock model resource ARN restrictions must remain in place (only Claude 3 models allowed)
- Streaming invocation capability must continue to work (with corrected namespace)
- Extraction pipeline's data structure and validation logic must remain unchanged
- Retry logic with exponential backoff must continue to function as implemented
- Transcription generation must continue to work exactly as before

**Scope:**
All operations that do NOT involve Bedrock model invocation should be completely unaffected by this fix. This includes:
- Comprehend Medical entity detection and analysis
- Transcription processing and text generation
- API request handling and response formatting (except for successful Bedrock invocations)
- Error handling and retry mechanisms for non-IAM errors
- Frontend JavaScript behavior and UI interactions

## Hypothesized Root Cause

Based on the bug description and AWS service architecture, the root cause is:

1. **Incorrect Service Namespace in IAM Policy**: The policy file `bedrock_comprehend_policy.json` uses `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream`, but AWS Bedrock has two separate service namespaces:
   - `bedrock:` - Used for control plane operations (model management, fine-tuning, etc.)
   - `bedrock-runtime:` - Used for data plane operations (model invocation, inference)
   
   The boto3 bedrock-runtime client uses the `bedrock-runtime:` namespace for all inference operations.

2. **Policy-Client Namespace Mismatch**: When the Python code creates a boto3 client with `boto3.client('bedrock-runtime')`, all API calls use the `bedrock-runtime:` namespace. The IAM policy evaluation fails because it only finds `bedrock:` permissions, not `bedrock-runtime:` permissions.

3. **Missing Deployment Verification**: The Terraform deployment process lacks automated testing to verify that the extraction pipeline works on ECS after infrastructure changes, allowing this misconfiguration to reach production.

## Correctness Properties

Property 1: Fault Condition - Bedrock Model Invocation Authorization

_For any_ Bedrock model invocation request where the boto3 bedrock-runtime client attempts to call `invoke_model()` or `invoke_model_with_response_stream()`, the fixed IAM policy SHALL grant the required `bedrock-runtime:InvokeModel` or `bedrock-runtime:InvokeModelWithResponseStream` permission, allowing the request to succeed and return structured prescription data without AccessDeniedException.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

Property 2: Preservation - Non-Bedrock Operations and Existing Permissions

_For any_ operation that does NOT involve Bedrock model invocation (Comprehend Medical operations, transcription processing, resource restrictions, retry logic), the fixed IAM policy SHALL produce exactly the same authorization behavior as the original policy, preserving all existing functionality for non-Bedrock operations and maintaining all security restrictions.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File 1**: `seva-arogya-infra/iam_policies/bedrock_comprehend_policy.json`

**Specific Changes**:
1. **Correct Bedrock Action Namespace**: Replace `bedrock:InvokeModel` with `bedrock-runtime:InvokeModel`
   - Change line with `"bedrock:InvokeModel"` to `"bedrock-runtime:InvokeModel"`
   - This aligns the policy with the boto3 bedrock-runtime client's required permissions

2. **Correct Streaming Action Namespace**: Replace `bedrock:InvokeModelWithResponseStream` with `bedrock-runtime:InvokeModelWithResponseStream`
   - Change line with `"bedrock:InvokeModelWithResponseStream"` to `"bedrock-runtime:InvokeModelWithResponseStream"`
   - This enables streaming responses with the correct namespace

3. **Preserve Comprehend Medical Permissions**: Keep all `comprehendmedical:*` actions unchanged
   - No modifications to Comprehend Medical permissions
   - Ensures entity detection continues to work

4. **Preserve Resource Restrictions**: Keep all Bedrock model resource ARNs unchanged
   - Maintain restrictions to Claude 3 models only
   - Security boundary remains intact

**File 2**: `seva-arogya-infra/main.tf` (or appropriate Terraform file)

**Specific Changes**:
1. **Add ECS Test Execution**: Add a `null_resource` with `local-exec` provisioner to run automated tests after ECS deployment
   - Execute test script that verifies extraction pipeline end-to-end
   - Depends on ECS service and task definition resources

2. **Create Test Script**: Add shell script that:
   - Waits for ECS service to be stable
   - Invokes extraction API with sample transcript
   - Verifies 200 response and valid prescription data structure
   - Fails Terraform apply if test fails

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed infrastructure, then verify the fix works correctly and preserves existing behavior.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that the IAM namespace mismatch is the root cause. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that attempt to invoke Bedrock models through the extraction API using the UNFIXED IAM policy. Run these tests against the current ECS deployment to observe AccessDeniedException failures and confirm the root cause.

**Test Cases**:
1. **Direct Model Invocation Test**: Call `bedrock_client.generate_prescription_data()` with a sample transcript (will fail on unfixed policy with AccessDeniedException)
2. **API Endpoint Test**: POST to `/api/v1/extract` with transcript data (will fail with 500 error on unfixed policy)
3. **Streaming Invocation Test**: Attempt streaming response with `invoke_model_with_response_stream()` (will fail on unfixed policy)
4. **IAM Policy Simulation Test**: Use AWS IAM Policy Simulator to test `bedrock-runtime:InvokeModel` action against current policy (will show "denied" on unfixed policy)

**Expected Counterexamples**:
- AccessDeniedException with message indicating missing `bedrock-runtime:InvokeModel` permission
- API returns 500 error with Bedrock invocation failure in logs
- IAM Policy Simulator shows "implicitly denied" for `bedrock-runtime:InvokeModel` action
- Possible causes: namespace mismatch (`bedrock:` vs `bedrock-runtime:`), missing action entirely, incorrect resource ARN

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (Bedrock model invocation attempts), the fixed IAM policy produces the expected behavior (successful authorization).

**Pseudocode:**
```
FOR ALL request WHERE isBugCondition(request) DO
  result := invokeBedrockModel_withFixedPolicy(request)
  ASSERT result.status == 'success'
  ASSERT result.response_contains_prescription_data == true
  ASSERT NOT result.error_type == 'AccessDeniedException'
END FOR
```

**Test Plan**: After applying the IAM policy fix, run the same test cases that failed during exploratory testing and verify they now succeed.

**Test Cases**:
1. **Fixed Model Invocation Test**: Call `bedrock_client.generate_prescription_data()` with sample transcript (should succeed with fixed policy)
2. **Fixed API Endpoint Test**: POST to `/api/v1/extract` with transcript data (should return 200 with prescription data)
3. **Fixed Streaming Test**: Verify streaming responses work with corrected namespace
4. **IAM Policy Simulator Verification**: Confirm `bedrock-runtime:InvokeModel` is now allowed

### Preservation Checking

**Goal**: Verify that for all operations where the bug condition does NOT hold (non-Bedrock operations), the fixed IAM policy produces the same authorization behavior as the original policy.

**Pseudocode:**
```
FOR ALL operation WHERE NOT isBugCondition(operation) DO
  ASSERT authorizeOperation_original(operation) == authorizeOperation_fixed(operation)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the operation domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that authorization behavior is unchanged for all non-Bedrock operations

**Test Plan**: Observe behavior on UNFIXED policy first for Comprehend Medical operations and other non-Bedrock functionality, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Comprehend Medical Preservation**: Verify `detect_entities_v2()` and other Comprehend operations continue to work (observe on unfixed, verify on fixed)
2. **Resource Restriction Preservation**: Verify that only Claude 3 models are accessible, other models still denied (observe on unfixed, verify on fixed)
3. **Transcription Preservation**: Verify transcription generation continues to work unchanged (observe on unfixed, verify on fixed)
4. **Retry Logic Preservation**: Verify exponential backoff retry behavior unchanged for rate limits (observe on unfixed, verify on fixed)

### Unit Tests

- Test IAM policy JSON syntax is valid after changes
- Test that `bedrock-runtime:InvokeModel` action is present in policy
- Test that `bedrock-runtime:InvokeModelWithResponseStream` action is present in policy
- Test that `comprehendmedical:*` actions remain unchanged
- Test that Bedrock model resource ARNs remain unchanged

### Property-Based Tests

- Generate random medical transcripts and verify extraction succeeds with fixed policy
- Generate random Comprehend Medical operations and verify they continue to work
- Generate random model IDs and verify resource restrictions still apply (only Claude 3 allowed)
- Test that all non-Bedrock AWS service calls continue to work across many scenarios

### Integration Tests

- Test full extraction flow: transcript → Bedrock invocation → prescription data generation
- Test ECS deployment with automated test execution in Terraform
- Test that extraction API returns 200 with valid prescription data structure
- Test that error handling and retry logic work correctly for non-IAM errors
- Test that frontend can successfully trigger extraction and receive results
