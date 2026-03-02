# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Fault Condition** - Bedrock Model Invocation Authorization
  - **CRITICAL**: This test MUST FAIL on unfixed policy - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the policy when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the IAM namespace mismatch
  - **Scoped PBT Approach**: Scope the property to concrete failing cases: InvokeModel and InvokeModelWithResponseStream actions with bedrock-runtime client
  - Test that IAM policy authorizes `bedrock-runtime:InvokeModel` and `bedrock-runtime:InvokeModelWithResponseStream` actions
  - Use AWS IAM Policy Simulator or actual Bedrock client invocation to verify authorization
  - Test cases:
    - Call `bedrock_client.generate_prescription_data()` with sample transcript
    - Call Bedrock with streaming enabled using `invoke_model_with_response_stream()`
    - Use IAM Policy Simulator to test `bedrock-runtime:InvokeModel` action against current policy
  - Run test on UNFIXED policy
  - **EXPECTED OUTCOME**: Test FAILS with AccessDeniedException mentioning `bedrock-runtime:InvokeModel` or `bedrock-runtime:InvokeModelWithResponseStream`
  - Document counterexamples found (specific error messages, denied actions from Policy Simulator)
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Non-Bedrock-Runtime Policy Elements
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED policy for non-buggy operations:
    - Comprehend Medical operations (`comprehendmedical:DetectEntitiesV2`)
    - Resource restrictions (attempt to invoke non-Claude-3 models)
    - Policy structure (statement count, Sids, Effects)
  - Write property-based tests capturing observed behavior patterns:
    - Test that Comprehend Medical operations succeed with current permissions
    - Test that non-Claude-3 models are denied (resource restriction works)
    - Test that policy has exactly 2 statements with expected Sids
    - Test that all non-Action fields in BedrockRuntimeAccess statement remain unchanged
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED policy
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed policy
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Fix IAM policy action namespace

  - [x] 3.1 Implement the fix
    - Open `seva-arogya-infra/iam_policies/bedrock_comprehend_policy.json`
    - Locate the `BedrockRuntimeAccess` statement (second statement in the policy)
    - Update Action array to use `bedrock-runtime:` namespace prefix:
      - Change `"bedrock:InvokeModel"` to `"bedrock-runtime:InvokeModel"`
      - Change `"bedrock:InvokeModelWithResponseStream"` to `"bedrock-runtime:InvokeModelWithResponseStream"`
    - Verify NO other changes are made (Sid, Effect, Resource must remain unchanged)
    - Verify JSON syntax is valid
    - _Bug_Condition: isBugCondition(action) where action.action IN ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'] AND action.intendedService == 'bedrock-runtime'_
    - _Expected_Behavior: For all Bedrock Runtime model invocations, IAM policy uses bedrock-runtime: namespace enabling successful authorization_
    - _Preservation: Comprehend Medical permissions, resource ARNs, statement structure, and all non-Action fields remain unchanged_
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Bedrock Model Invocation Authorization
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms IAM namespace is fixed and Bedrock invocations are authorized)
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Bedrock-Runtime Policy Elements
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions in Comprehend Medical, resource restrictions, or policy structure)
    - Confirm all tests still pass after fix (no regressions)

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
