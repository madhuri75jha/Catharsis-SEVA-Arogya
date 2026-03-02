# Bedrock IAM Permissions Fix Design

## Overview

This bugfix addresses an IAM policy misconfiguration that prevents the medical extraction feature from invoking AWS Bedrock models. The IAM policy file `seva-arogya-infra/iam_policies/bedrock_comprehend_policy.json` uses the incorrect action namespace `bedrock:*` instead of `bedrock-runtime:*` for model invocation operations. This causes AccessDeniedException errors when the extraction pipeline attempts to generate prescription data from medical transcripts.

The fix is straightforward: update the action namespace from `bedrock:` to `bedrock-runtime:` for the two model invocation actions. This is a minimal, targeted change that aligns the IAM policy with AWS Bedrock Runtime service requirements without affecting any other permissions or functionality.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when the extraction pipeline invokes Bedrock models using the boto3 bedrock-runtime client, but the IAM policy grants permissions using the wrong `bedrock:` namespace
- **Property (P)**: The desired behavior - Bedrock model invocations should succeed with proper authorization using `bedrock-runtime:InvokeModel` and `bedrock-runtime:InvokeModelWithResponseStream` permissions
- **Preservation**: Existing Comprehend Medical permissions and Bedrock resource restrictions that must remain unchanged by the fix
- **bedrock_client.generate_prescription_data()**: The function in `aws_services/bedrock_client.py` that invokes Bedrock models to generate structured prescription data from transcripts
- **ECS task role**: The IAM role (seva-arogya-dev-ecs-task-role) assumed by the ECS container that needs permissions to invoke Bedrock models

## Bug Details

### Fault Condition

The bug manifests when the extraction pipeline attempts to invoke AWS Bedrock models for prescription data generation. The IAM policy grants permissions using the `bedrock:` action namespace, but the boto3 bedrock-runtime client requires the `bedrock-runtime:` namespace for model invocation operations.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type IAMPolicyAction
  OUTPUT: boolean
  
  RETURN input.action IN ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream']
         AND input.intendedService == 'bedrock-runtime'
         AND input.actualServiceNamespace != input.intendedService
END FUNCTION
```

### Examples

- **Example 1**: Extraction pipeline calls `bedrock_client.generate_prescription_data(transcript)` → boto3 client invokes `client.invoke_model()` → AWS IAM checks for `bedrock-runtime:InvokeModel` permission → Policy only grants `bedrock:InvokeModel` → AccessDeniedException raised
- **Example 2**: Streaming response call uses `client.invoke_model_with_response_stream()` → AWS IAM checks for `bedrock-runtime:InvokeModelWithResponseStream` permission → Policy only grants `bedrock:InvokeModelWithResponseStream` → AccessDeniedException raised
- **Example 3**: Comprehend Medical call uses `client.detect_entities_v2()` → AWS IAM checks for `comprehendmedical:DetectEntitiesV2` permission → Policy correctly grants `comprehendmedical:DetectEntitiesV2` → Operation succeeds (not affected by bug)
- **Edge case**: If a future update adds new Bedrock Runtime actions (e.g., `InvokeAgent`), they would also need the `bedrock-runtime:` namespace to work correctly

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Comprehend Medical operations must continue to work with existing `comprehendmedical:*` permissions
- Bedrock model resource restrictions must remain unchanged (only Claude 3 models allowed)
- Retry logic and error handling in the extraction pipeline must continue to work
- Prescription data structure and validation logic must remain unchanged

**Scope:**
All IAM policy elements that do NOT involve the Bedrock Runtime action namespace should be completely unaffected by this fix. This includes:
- The ComprehendMedicalAccess statement (Sid, Effect, Action, Resource)
- The BedrockRuntimeAccess statement's Sid, Effect, and Resource fields
- Resource ARN patterns restricting access to specific Claude 3 models
- Any other IAM policies or roles in the infrastructure

## Hypothesized Root Cause

Based on the bug description and IAM policy analysis, the root cause is:

1. **Incorrect Service Namespace**: The policy uses `bedrock:` as the action namespace, but AWS Bedrock has two separate services:
   - `bedrock` service: Used for management operations (listing models, managing fine-tuning jobs)
   - `bedrock-runtime` service: Used for inference operations (invoking models)
   
2. **Documentation Confusion**: The policy creator may have assumed all Bedrock operations use the `bedrock:` namespace, not realizing that runtime operations require a separate namespace

3. **No Validation at Policy Creation**: The IAM policy was created and applied without testing actual model invocation, so the namespace mismatch was not caught until runtime

4. **Boto3 Client Mismatch**: The code correctly uses `boto3.client('bedrock-runtime')`, but the IAM policy was written for `boto3.client('bedrock')` operations

## Correctness Properties

Property 1: Fault Condition - Bedrock Model Invocation Authorization

_For any_ IAM policy action where the action is intended for Bedrock Runtime model invocation (InvokeModel or InvokeModelWithResponseStream), the fixed IAM policy SHALL use the `bedrock-runtime:` namespace prefix, enabling successful authorization when the boto3 bedrock-runtime client invokes models.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation - Non-Bedrock-Runtime Policy Elements

_For any_ IAM policy element that is NOT a Bedrock Runtime action namespace (Comprehend Medical permissions, resource ARNs, statement structure), the fixed IAM policy SHALL contain exactly the same values as the original policy, preserving all existing permissions and restrictions.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct (incorrect service namespace):

**File**: `seva-arogya-infra/iam_policies/bedrock_comprehend_policy.json`

**Statement**: `BedrockRuntimeAccess` (second statement in the policy)

**Specific Changes**:
1. **Action Namespace Correction**: Update the Action array to use `bedrock-runtime:` prefix
   - Change `"bedrock:InvokeModel"` to `"bedrock-runtime:InvokeModel"`
   - Change `"bedrock:InvokeModelWithResponseStream"` to `"bedrock-runtime:InvokeModelWithResponseStream"`

2. **No Other Changes**: All other fields remain unchanged
   - Sid: `"BedrockRuntimeAccess"` (unchanged)
   - Effect: `"Allow"` (unchanged)
   - Resource: Array of Claude 3 model ARNs (unchanged)

3. **Verification**: After applying the fix, the policy must be redeployed to the ECS task role for the changes to take effect

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on the unfixed policy, then verify the fix works correctly and preserves existing behavior.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that the incorrect namespace is the root cause.

**Test Plan**: Attempt to invoke Bedrock models using the current IAM policy and observe AccessDeniedException errors. Verify that the error message specifically mentions the missing `bedrock-runtime:InvokeModel` permission.

**Test Cases**:
1. **Model Invocation Test**: Call `bedrock_client.generate_prescription_data()` with a sample transcript (will fail on unfixed policy with AccessDeniedException mentioning `bedrock-runtime:InvokeModel`)
2. **Streaming Response Test**: Call Bedrock with streaming enabled (will fail on unfixed policy with AccessDeniedException mentioning `bedrock-runtime:InvokeModelWithResponseStream`)
3. **Comprehend Medical Test**: Call Comprehend Medical operations (should succeed on unfixed policy, confirming those permissions are correct)
4. **IAM Policy Simulator Test**: Use AWS IAM Policy Simulator to test `bedrock-runtime:InvokeModel` action against the current policy (will show "Denied")

**Expected Counterexamples**:
- AccessDeniedException with message containing "bedrock-runtime:InvokeModel" or "bedrock-runtime:InvokeModelWithResponseStream"
- IAM Policy Simulator shows "Denied" for bedrock-runtime actions but "Allowed" for bedrock actions
- Possible confirmation: AWS CloudTrail logs show denied API calls to bedrock-runtime service

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (Bedrock Runtime model invocations), the fixed policy produces the expected behavior (successful authorization).

**Pseudocode:**
```
FOR ALL action WHERE isBugCondition(action) DO
  result := invokeBedrockModel_withFixedPolicy(action)
  ASSERT result.authorized == true
  ASSERT result.error == null
END FOR
```

**Test Plan**: After applying the namespace fix, invoke Bedrock models and verify successful execution without AccessDeniedException.

**Test Cases**:
1. **Model Invocation Success**: Call `bedrock_client.generate_prescription_data()` with a sample transcript → Should return structured prescription data without errors
2. **Streaming Response Success**: Call Bedrock with streaming enabled → Should return streaming response without errors
3. **IAM Policy Simulator Verification**: Use AWS IAM Policy Simulator to test `bedrock-runtime:InvokeModel` action against the fixed policy → Should show "Allowed"
4. **End-to-End Extraction Pipeline**: Run the full extraction pipeline from transcript to prescription data → Should complete successfully

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (non-Bedrock-Runtime operations), the fixed policy produces the same result as the original policy.

**Pseudocode:**
```
FOR ALL policyElement WHERE NOT isBugCondition(policyElement) DO
  ASSERT originalPolicy[policyElement] == fixedPolicy[policyElement]
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It can verify that all non-modified policy elements remain identical
- It catches unintended changes to resource ARNs, statement structure, or other permissions
- It provides strong guarantees that Comprehend Medical and resource restrictions are unchanged

**Test Plan**: Verify that Comprehend Medical operations, resource restrictions, and other policy elements continue to work exactly as before.

**Test Cases**:
1. **Comprehend Medical Preservation**: Call `comprehendmedical:DetectEntitiesV2` → Should succeed with same behavior as before fix
2. **Resource Restriction Preservation**: Attempt to invoke a non-Claude-3 model (e.g., Titan) → Should be denied with same error as before fix
3. **Policy Structure Preservation**: Compare original and fixed policy JSON (excluding the two modified actions) → Should be byte-for-byte identical
4. **Statement Count Preservation**: Verify policy still has exactly 2 statements with same Sids

### Unit Tests

- Test IAM policy JSON syntax is valid after modification
- Test that exactly 2 actions are modified (InvokeModel and InvokeModelWithResponseStream)
- Test that all other policy fields remain unchanged
- Test that resource ARNs still restrict to Claude 3 models only

### Property-Based Tests

- Generate random Bedrock Runtime actions and verify they are authorized with fixed policy
- Generate random Comprehend Medical operations and verify they continue to work
- Generate random model ARNs and verify resource restrictions are preserved
- Test that policy structure (statements, sids, effects) remains consistent

### Integration Tests

- Test full extraction pipeline flow: transcript → Comprehend Medical → Bedrock → prescription data
- Test error handling: verify retry logic still works for rate limits and service errors
- Test with multiple Claude 3 model variants to ensure all resource ARNs work
- Test that unauthorized models (non-Claude-3) are still blocked after fix
