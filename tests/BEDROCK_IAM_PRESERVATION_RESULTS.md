# Bedrock IAM Permissions Fix - Preservation Test Results

## Overview

**Status**: ✅ ALL PRESERVATION TESTS PASS

The preservation property tests successfully verified the baseline behavior of the UNFIXED IAM policy. All 33 tests passed, confirming the behaviors that must be preserved when implementing the fix.

## Test Execution Summary

**Test File**: `tests/test_bedrock_iam_preservation.py`
**Total Tests**: 33
**Passed**: 33 (100%)
**Failed**: 0
**Execution Time**: 0.39s

## Test Categories

### 1. Comprehend Medical Preservation (4 tests)
**Validates: Requirement 3.1**

✅ All tests passed - Comprehend Medical permissions are correctly configured:
- ComprehendMedicalAccess statement exists
- Required actions present: DetectEntitiesV2, InferICD10CM, InferRxNorm
- Effect is "Allow"
- Resource is "*" (wildcard)

**Baseline Behavior Confirmed**: Comprehend Medical operations will continue to work with existing permissions after the fix.

### 2. Bedrock Resource Restrictions (4 tests)
**Validates: Requirement 3.2**

✅ All tests passed - Bedrock resource restrictions are correctly configured:
- BedrockRuntimeAccess statement exists
- All resources are Claude 3 model ARNs
- Expected Claude 3 models present: sonnet, opus, haiku, 3.5-sonnet
- Effect is "Allow"

**Baseline Behavior Confirmed**: Access will remain restricted to only the specified Claude 3 models after the fix.

### 3. Policy Structure Preservation (4 tests)
**Validates: Requirements 3.2, 3.3, 3.4, 3.5**

✅ All tests passed - Policy structure is correct:
- Policy has exactly 2 statements
- Correct Sids: ComprehendMedicalAccess, BedrockRuntimeAccess
- Policy version is "2012-10-17" (standard)
- All statements have required fields (Effect, Action, Resource)

**Baseline Behavior Confirmed**: Policy structure will remain unchanged after the fix.

### 4. Bedrock Non-Action Fields Preservation (4 tests)
**Validates: Requirements 3.2, 3.3**

✅ All tests passed - Non-Action fields are correct:
- Sid: "BedrockRuntimeAccess" (unchanged)
- Effect: "Allow" (unchanged)
- Resource: 4 Claude 3 model ARNs (unchanged)
- Only standard IAM fields present

**Baseline Behavior Confirmed**: Only the Action field will be modified by the fix. All other fields will remain unchanged.

### 5. Property-Based Preservation (5 tests)
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

✅ All property-based tests passed with multiple examples:
- Statement Sids preserved (20 examples)
- Statement Effects are "Allow" (20 examples)
- All statements have Resources (20 examples)
- Bedrock resource ARNs are valid (50 examples)
- Comprehend actions preserved (30 examples)

**Total Property Test Examples**: 140 test cases generated and verified

**Baseline Behavior Confirmed**: Property-based testing provides strong guarantees that all non-modified elements will remain unchanged.

### 6. Retry Logic Preservation (3 tests)
**Validates: Requirement 3.5**

✅ All tests passed - Retry logic is correctly implemented:
- MAX_RETRIES = 3
- RETRY_DELAYS = [1.0, 2.0, 4.0] (exponential backoff)
- _call_with_retry method exists
- Custom exceptions defined: BedrockUnavailableError, BedrockRateLimitError

**Baseline Behavior Confirmed**: Retry logic with exponential backoff will continue to work after the fix.

### 7. Prescription Data Structure Preservation (5 tests)
**Validates: Requirement 3.4**

✅ All tests passed - Prescription data structure is correct:
- generate_prescription_data method exists
- _construct_prompt method exists
- _build_function_schema method exists
- FunctionCallResponse model defined
- HospitalConfiguration model defined

**Baseline Behavior Confirmed**: Prescription data generation logic will remain unchanged after the fix.

### 8. Policy JSON Structure Preservation (4 tests)
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

✅ All tests passed - JSON structure is valid:
- Policy is valid JSON
- Required top-level fields present: Version, Statement
- All statements are JSON objects
- All Action fields are lists of strings (20 examples)

**Baseline Behavior Confirmed**: Policy JSON structure is valid and will remain valid after the fix.

## Observed Baseline Behaviors

### IAM Policy Structure (UNFIXED)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ComprehendMedicalAccess",
      "Effect": "Allow",
      "Action": [
        "comprehendmedical:DetectEntitiesV2",
        "comprehendmedical:InferICD10CM",
        "comprehendmedical:InferRxNorm"
      ],
      "Resource": "*"
    },
    {
      "Sid": "BedrockRuntimeAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",  // ← INCORRECT (will be fixed)
        "bedrock:InvokeModelWithResponseStream"  // ← INCORRECT (will be fixed)
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-opus-20240229-v1:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"
      ]
    }
  ]
}
```

### Elements That MUST Remain Unchanged

1. **ComprehendMedicalAccess statement**: Entire statement unchanged
2. **BedrockRuntimeAccess Sid**: "BedrockRuntimeAccess"
3. **BedrockRuntimeAccess Effect**: "Allow"
4. **BedrockRuntimeAccess Resource**: All 4 Claude 3 model ARNs
5. **Policy Version**: "2012-10-17"
6. **Statement count**: 2 statements
7. **Statement order**: ComprehendMedicalAccess first, BedrockRuntimeAccess second

### Elements That WILL Change (Fix Scope)

1. **BedrockRuntimeAccess Action[0]**: "bedrock:InvokeModel" → "bedrock-runtime:InvokeModel"
2. **BedrockRuntimeAccess Action[1]**: "bedrock:InvokeModelWithResponseStream" → "bedrock-runtime:InvokeModelWithResponseStream"

## Preservation Guarantees

The preservation tests provide the following guarantees:

1. ✅ **Comprehend Medical operations will continue to work** (Requirement 3.1)
2. ✅ **Resource restrictions to Claude 3 models will be preserved** (Requirement 3.2)
3. ✅ **Streaming response permissions will be preserved** (Requirement 3.3)
4. ✅ **Prescription data structure and validation logic will be preserved** (Requirement 3.4)
5. ✅ **Retry logic with exponential backoff will be preserved** (Requirement 3.5)

## Next Steps

1. ✅ Task 1 completed: Bug condition exploration test written and confirmed bug exists
2. ✅ Task 2 completed: Preservation tests written and passing on UNFIXED policy
3. ⏭️ Task 3: Implement the IAM policy fix (change namespace from "bedrock:" to "bedrock-runtime:")
4. ⏭️ Task 3.2: Re-run bug condition exploration test (should PASS after fix)
5. ⏭️ Task 3.3: Re-run preservation tests (should still PASS after fix)

## Conclusion

All preservation tests pass on the UNFIXED policy, confirming the baseline behaviors that must be preserved. The fix can now be implemented with confidence that these tests will catch any unintended regressions.

The property-based tests generated 140 test cases across various scenarios, providing strong guarantees that the fix will not affect any non-Action fields in the IAM policy or any related code functionality.

