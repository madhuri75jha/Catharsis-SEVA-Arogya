"""
Preservation Property Tests for Bedrock IAM Permissions Fix

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

IMPORTANT: Follow observation-first methodology
- Observe behavior on UNFIXED policy for non-buggy operations
- Write property-based tests capturing observed behavior patterns
- Run tests on UNFIXED policy
- EXPECTED OUTCOME: Tests PASS (confirms baseline behavior to preserve)

This test suite verifies that the IAM policy fix preserves all existing
functionality that is NOT related to the Bedrock Runtime action namespace bug.

Property 2: Preservation - Non-Bedrock-Runtime Policy Elements

For any IAM policy element that is NOT a Bedrock Runtime action namespace
(Comprehend Medical permissions, resource ARNs, statement structure), the fixed
IAM policy SHALL contain exactly the same values as the original policy,
preserving all existing permissions and restrictions.
"""
import pytest
import json
import copy
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any, List


def get_iam_policy() -> Dict[str, Any]:
    """
    Load the IAM policy from the JSON file.
    
    Returns dict with policy content or raises FileNotFoundError.
    """
    policy_path = 'seva-arogya-infra/iam_policies/bedrock_comprehend_policy.json'
    with open(policy_path, 'r') as f:
        return json.load(f)


def get_policy_statement_by_sid(policy: Dict[str, Any], sid: str) -> Dict[str, Any]:
    """Get a specific statement from the policy by Sid"""
    for statement in policy.get('Statement', []):
        if statement.get('Sid') == sid:
            return statement
    return {}



class TestComprehendMedicalPreservation:
    """
    Test that Comprehend Medical permissions are preserved.
    
    **Validates: Requirement 3.1**
    
    WHEN the extraction pipeline calls Comprehend Medical operations
    THEN the system SHALL CONTINUE TO successfully extract medical entities
    using the existing comprehendmedical:* permissions
    """
    
    def test_comprehend_medical_statement_exists(self):
        """
        Test that ComprehendMedicalAccess statement exists in the policy.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        
        # Find ComprehendMedicalAccess statement
        comprehend_statement = get_policy_statement_by_sid(policy, 'ComprehendMedicalAccess')
        
        assert comprehend_statement, (
            "ComprehendMedicalAccess statement not found in IAM policy"
        )
    
    def test_comprehend_medical_has_required_actions(self):
        """
        Test that all required Comprehend Medical actions are present.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        
        **Validates: Requirement 3.1**
        """
        policy = get_iam_policy()
        comprehend_statement = get_policy_statement_by_sid(policy, 'ComprehendMedicalAccess')
        
        assert comprehend_statement, "ComprehendMedicalAccess statement not found"
        
        actions = comprehend_statement.get('Action', [])
        
        # Required actions for medical entity extraction
        required_actions = [
            'comprehendmedical:DetectEntitiesV2',
            'comprehendmedical:InferICD10CM',
            'comprehendmedical:InferRxNorm'
        ]
        
        for required_action in required_actions:
            assert required_action in actions, (
                f"Required Comprehend Medical action '{required_action}' not found. "
                f"Actions in policy: {actions}"
            )
    
    def test_comprehend_medical_effect_is_allow(self):
        """
        Test that ComprehendMedicalAccess statement has Effect: Allow.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        comprehend_statement = get_policy_statement_by_sid(policy, 'ComprehendMedicalAccess')
        
        assert comprehend_statement, "ComprehendMedicalAccess statement not found"
        
        effect = comprehend_statement.get('Effect')
        assert effect == 'Allow', (
            f"ComprehendMedicalAccess Effect should be 'Allow', found: {effect}"
        )
    
    def test_comprehend_medical_resource_is_wildcard(self):
        """
        Test that ComprehendMedicalAccess allows all resources (*).
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        comprehend_statement = get_policy_statement_by_sid(policy, 'ComprehendMedicalAccess')
        
        assert comprehend_statement, "ComprehendMedicalAccess statement not found"
        
        resource = comprehend_statement.get('Resource')
        assert resource == '*', (
            f"ComprehendMedicalAccess Resource should be '*', found: {resource}"
        )



class TestBedrockResourceRestrictions:
    """
    Test that Bedrock resource restrictions are preserved.
    
    **Validates: Requirement 3.2**
    
    WHEN the IAM policy specifies Bedrock model resource ARNs
    THEN the system SHALL CONTINUE TO restrict access to only the specified
    Claude 3 models
    """
    
    def test_bedrock_statement_exists(self):
        """
        Test that BedrockRuntimeAccess statement exists in the policy.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        
        bedrock_statement = get_policy_statement_by_sid(policy, 'BedrockRuntimeAccess')
        
        assert bedrock_statement, (
            "BedrockRuntimeAccess statement not found in IAM policy"
        )
    
    def test_bedrock_resources_are_claude3_models(self):
        """
        Test that all Bedrock resources are Claude 3 model ARNs.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        
        **Validates: Requirement 3.2**
        """
        policy = get_iam_policy()
        bedrock_statement = get_policy_statement_by_sid(policy, 'BedrockRuntimeAccess')
        
        assert bedrock_statement, "BedrockRuntimeAccess statement not found"
        
        resources = bedrock_statement.get('Resource', [])
        
        assert len(resources) > 0, "No resources specified in BedrockRuntimeAccess"
        
        # All resources should be Claude 3 model ARNs
        for resource in resources:
            assert isinstance(resource, str), f"Resource should be string, got: {type(resource)}"
            assert 'arn:aws:bedrock:' in resource, (
                f"Resource '{resource}' is not a Bedrock ARN"
            )
            assert 'foundation-model/anthropic.claude-3' in resource, (
                f"Resource '{resource}' is not a Claude 3 model ARN"
            )
    
    def test_bedrock_has_expected_claude3_models(self):
        """
        Test that the policy includes expected Claude 3 model variants.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        
        **Validates: Requirement 3.2**
        """
        policy = get_iam_policy()
        bedrock_statement = get_policy_statement_by_sid(policy, 'BedrockRuntimeAccess')
        
        assert bedrock_statement, "BedrockRuntimeAccess statement not found"
        
        resources = bedrock_statement.get('Resource', [])
        resource_str = ' '.join(resources)
        
        # Expected Claude 3 model families
        expected_models = [
            'claude-3-sonnet',
            'claude-3-opus',
            'claude-3-haiku',
            'claude-3-5-sonnet'
        ]
        
        for model in expected_models:
            assert model in resource_str, (
                f"Expected Claude 3 model '{model}' not found in resources. "
                f"Resources: {resources}"
            )
    
    def test_bedrock_effect_is_allow(self):
        """
        Test that BedrockRuntimeAccess statement has Effect: Allow.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        bedrock_statement = get_policy_statement_by_sid(policy, 'BedrockRuntimeAccess')
        
        assert bedrock_statement, "BedrockRuntimeAccess statement not found"
        
        effect = bedrock_statement.get('Effect')
        assert effect == 'Allow', (
            f"BedrockRuntimeAccess Effect should be 'Allow', found: {effect}"
        )



class TestPolicyStructurePreservation:
    """
    Test that IAM policy structure is preserved.
    
    **Validates: Requirements 3.2, 3.3, 3.4, 3.5**
    
    WHEN the IAM policy is modified to fix the namespace bug
    THEN the policy structure (statement count, Sids, Effects, Resources)
    SHALL remain unchanged
    """
    
    def test_policy_has_two_statements(self):
        """
        Test that the policy has exactly 2 statements.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        
        statements = policy.get('Statement', [])
        
        assert len(statements) == 2, (
            f"Expected 2 statements in IAM policy, found {len(statements)}"
        )
    
    def test_policy_has_correct_sids(self):
        """
        Test that the policy has the expected statement Sids.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        
        statements = policy.get('Statement', [])
        sids = [stmt.get('Sid') for stmt in statements]
        
        assert 'ComprehendMedicalAccess' in sids, (
            "Missing ComprehendMedicalAccess statement"
        )
        assert 'BedrockRuntimeAccess' in sids, (
            "Missing BedrockRuntimeAccess statement"
        )
    
    def test_policy_version_is_standard(self):
        """
        Test that the policy uses the standard IAM policy version.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        
        version = policy.get('Version')
        assert version == '2012-10-17', (
            f"Expected IAM policy version '2012-10-17', found: {version}"
        )
    
    def test_all_statements_have_required_fields(self):
        """
        Test that all statements have required IAM policy fields.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        
        statements = policy.get('Statement', [])
        
        for statement in statements:
            sid = statement.get('Sid', 'Unknown')
            
            # Required fields
            assert 'Effect' in statement, (
                f"Statement '{sid}' missing 'Effect' field"
            )
            assert 'Action' in statement, (
                f"Statement '{sid}' missing 'Action' field"
            )
            assert 'Resource' in statement, (
                f"Statement '{sid}' missing 'Resource' field"
            )
            
            # Effect should be Allow or Deny
            effect = statement.get('Effect')
            assert effect in ['Allow', 'Deny'], (
                f"Statement '{sid}' has invalid Effect: {effect}"
            )



class TestBedrockNonActionFieldsPreservation:
    """
    Test that non-Action fields in BedrockRuntimeAccess are preserved.
    
    **Validates: Requirements 3.2, 3.3**
    
    The fix should ONLY modify the Action field. All other fields
    (Sid, Effect, Resource) must remain unchanged.
    """
    
    def test_bedrock_sid_unchanged(self):
        """
        Test that BedrockRuntimeAccess Sid is unchanged.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        bedrock_statement = get_policy_statement_by_sid(policy, 'BedrockRuntimeAccess')
        
        assert bedrock_statement, "BedrockRuntimeAccess statement not found"
        
        sid = bedrock_statement.get('Sid')
        assert sid == 'BedrockRuntimeAccess', (
            f"BedrockRuntimeAccess Sid should be 'BedrockRuntimeAccess', found: {sid}"
        )
    
    def test_bedrock_effect_unchanged(self):
        """
        Test that BedrockRuntimeAccess Effect is unchanged.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        bedrock_statement = get_policy_statement_by_sid(policy, 'BedrockRuntimeAccess')
        
        assert bedrock_statement, "BedrockRuntimeAccess statement not found"
        
        effect = bedrock_statement.get('Effect')
        assert effect == 'Allow', (
            f"BedrockRuntimeAccess Effect should be 'Allow', found: {effect}"
        )
    
    def test_bedrock_resource_unchanged(self):
        """
        Test that BedrockRuntimeAccess Resource list is unchanged.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        
        **Validates: Requirement 3.2**
        """
        policy = get_iam_policy()
        bedrock_statement = get_policy_statement_by_sid(policy, 'BedrockRuntimeAccess')
        
        assert bedrock_statement, "BedrockRuntimeAccess statement not found"
        
        resources = bedrock_statement.get('Resource', [])
        
        # Expected resources (Claude 3 models)
        expected_resources = [
            'arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0',
            'arn:aws:bedrock:*::foundation-model/anthropic.claude-3-opus-20240229-v1:0',
            'arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-20240307-v1:0',
            'arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0'
        ]
        
        assert len(resources) == len(expected_resources), (
            f"Expected {len(expected_resources)} resources, found {len(resources)}"
        )
        
        for expected_resource in expected_resources:
            assert expected_resource in resources, (
                f"Expected resource '{expected_resource}' not found in policy. "
                f"Resources: {resources}"
            )
    
    def test_bedrock_has_only_standard_fields(self):
        """
        Test that BedrockRuntimeAccess has only standard IAM fields.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        bedrock_statement = get_policy_statement_by_sid(policy, 'BedrockRuntimeAccess')
        
        assert bedrock_statement, "BedrockRuntimeAccess statement not found"
        
        # Standard IAM statement fields
        allowed_fields = {'Sid', 'Effect', 'Action', 'Resource', 'Condition', 'Principal', 'NotAction', 'NotResource'}
        
        actual_fields = set(bedrock_statement.keys())
        
        # All actual fields should be in allowed fields
        unexpected_fields = actual_fields - allowed_fields
        assert not unexpected_fields, (
            f"BedrockRuntimeAccess has unexpected fields: {unexpected_fields}"
        )



class TestPropertyBasedPreservation:
    """
    Property-based tests for preservation guarantees.
    
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
    
    These tests use property-based testing to verify that all non-Action
    fields remain unchanged across many test cases.
    """
    
    @given(st.sampled_from(['ComprehendMedicalAccess', 'BedrockRuntimeAccess']))
    @settings(max_examples=20)
    def test_statement_sids_are_preserved(self, sid):
        """
        Property: All statement Sids must be preserved.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        statement = get_policy_statement_by_sid(policy, sid)
        
        assert statement, f"Statement with Sid '{sid}' not found"
        assert statement.get('Sid') == sid, (
            f"Statement Sid mismatch: expected '{sid}', found '{statement.get('Sid')}'"
        )
    
    @given(st.sampled_from(['ComprehendMedicalAccess', 'BedrockRuntimeAccess']))
    @settings(max_examples=20)
    def test_statement_effects_are_allow(self, sid):
        """
        Property: All statement Effects must be 'Allow'.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        statement = get_policy_statement_by_sid(policy, sid)
        
        assert statement, f"Statement with Sid '{sid}' not found"
        assert statement.get('Effect') == 'Allow', (
            f"Statement '{sid}' Effect should be 'Allow', found: {statement.get('Effect')}"
        )
    
    @given(st.sampled_from(['ComprehendMedicalAccess', 'BedrockRuntimeAccess']))
    @settings(max_examples=20)
    def test_statement_has_resources(self, sid):
        """
        Property: All statements must have Resource field.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        statement = get_policy_statement_by_sid(policy, sid)
        
        assert statement, f"Statement with Sid '{sid}' not found"
        assert 'Resource' in statement, (
            f"Statement '{sid}' missing 'Resource' field"
        )
    
    @settings(max_examples=50)
    @given(st.integers(min_value=0, max_value=3))
    def test_bedrock_resource_arns_are_valid(self, resource_index):
        """
        Property: All Bedrock resource ARNs must be valid Claude 3 model ARNs.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        
        **Validates: Requirement 3.2**
        """
        policy = get_iam_policy()
        bedrock_statement = get_policy_statement_by_sid(policy, 'BedrockRuntimeAccess')
        
        assert bedrock_statement, "BedrockRuntimeAccess statement not found"
        
        resources = bedrock_statement.get('Resource', [])
        
        # Skip if resource_index is out of bounds
        assume(resource_index < len(resources))
        
        resource = resources[resource_index]
        
        # Validate ARN structure
        assert resource.startswith('arn:aws:bedrock:'), (
            f"Resource ARN should start with 'arn:aws:bedrock:', found: {resource}"
        )
        assert 'foundation-model/anthropic.claude-3' in resource, (
            f"Resource should be a Claude 3 model, found: {resource}"
        )
        
        # Validate ARN format: arn:aws:bedrock:region:account:foundation-model/model-id
        parts = resource.split(':')
        assert len(parts) >= 6, (
            f"Invalid ARN format: {resource}"
        )
        assert parts[0] == 'arn', f"ARN should start with 'arn', found: {parts[0]}"
        assert parts[1] == 'aws', f"ARN should have 'aws' partition, found: {parts[1]}"
        assert parts[2] == 'bedrock', f"ARN should be for 'bedrock' service, found: {parts[2]}"
    
    @settings(max_examples=30)
    @given(st.sampled_from([
        'comprehendmedical:DetectEntitiesV2',
        'comprehendmedical:InferICD10CM',
        'comprehendmedical:InferRxNorm'
    ]))
    def test_comprehend_actions_are_preserved(self, action):
        """
        Property: All Comprehend Medical actions must be preserved.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        
        **Validates: Requirement 3.1**
        """
        policy = get_iam_policy()
        comprehend_statement = get_policy_statement_by_sid(policy, 'ComprehendMedicalAccess')
        
        assert comprehend_statement, "ComprehendMedicalAccess statement not found"
        
        actions = comprehend_statement.get('Action', [])
        
        assert action in actions, (
            f"Comprehend Medical action '{action}' not found in policy. "
            f"Actions: {actions}"
        )



class TestRetryLogicPreservation:
    """
    Test that retry logic and error handling are preserved.
    
    **Validates: Requirement 3.5**
    
    WHEN the Bedrock client encounters rate limits or service unavailability
    THEN the system SHALL CONTINUE TO retry with exponential backoff as
    implemented in _call_with_retry()
    
    Note: This tests the code structure, not the IAM policy directly.
    The IAM fix should not affect retry logic.
    """
    
    def test_bedrock_client_has_retry_configuration(self):
        """
        Test that BedrockClient has retry configuration constants.
        
        EXPECTED: PASS on unfixed code (baseline behavior)
        """
        from aws_services.bedrock_client import BedrockClient
        
        # Check retry configuration exists
        assert hasattr(BedrockClient, 'MAX_RETRIES'), (
            "BedrockClient missing MAX_RETRIES constant"
        )
        assert hasattr(BedrockClient, 'RETRY_DELAYS'), (
            "BedrockClient missing RETRY_DELAYS constant"
        )
        
        # Verify retry configuration values
        assert BedrockClient.MAX_RETRIES == 3, (
            f"Expected MAX_RETRIES=3, found: {BedrockClient.MAX_RETRIES}"
        )
        assert BedrockClient.RETRY_DELAYS == [1.0, 2.0, 4.0], (
            f"Expected RETRY_DELAYS=[1.0, 2.0, 4.0], found: {BedrockClient.RETRY_DELAYS}"
        )
    
    def test_bedrock_client_has_retry_method(self):
        """
        Test that BedrockClient has _call_with_retry method.
        
        EXPECTED: PASS on unfixed code (baseline behavior)
        """
        from aws_services.bedrock_client import BedrockClient
        
        assert hasattr(BedrockClient, '_call_with_retry'), (
            "BedrockClient missing _call_with_retry method"
        )
        
        # Verify it's a callable method
        assert callable(getattr(BedrockClient, '_call_with_retry')), (
            "_call_with_retry should be a callable method"
        )
    
    def test_bedrock_client_has_custom_exceptions(self):
        """
        Test that custom Bedrock exceptions are defined.
        
        EXPECTED: PASS on unfixed code (baseline behavior)
        """
        from aws_services import bedrock_client
        
        assert hasattr(bedrock_client, 'BedrockUnavailableError'), (
            "BedrockUnavailableError exception not defined"
        )
        assert hasattr(bedrock_client, 'BedrockRateLimitError'), (
            "BedrockRateLimitError exception not defined"
        )
        
        # Verify they are Exception subclasses
        assert issubclass(bedrock_client.BedrockUnavailableError, Exception), (
            "BedrockUnavailableError should be an Exception subclass"
        )
        assert issubclass(bedrock_client.BedrockRateLimitError, Exception), (
            "BedrockRateLimitError should be an Exception subclass"
        )


class TestPrescriptionDataStructurePreservation:
    """
    Test that prescription data structure and validation logic are preserved.
    
    **Validates: Requirement 3.4**
    
    WHEN the extraction pipeline processes transcripts with valid medical entities
    THEN the system SHALL CONTINUE TO generate prescription data with the same
    structure and validation logic
    
    Note: This tests the code structure, not the IAM policy directly.
    """
    
    def test_bedrock_client_has_generate_prescription_data_method(self):
        """
        Test that BedrockClient has generate_prescription_data method.
        
        EXPECTED: PASS on unfixed code (baseline behavior)
        """
        from aws_services.bedrock_client import BedrockClient
        
        assert hasattr(BedrockClient, 'generate_prescription_data'), (
            "BedrockClient missing generate_prescription_data method"
        )
        
        # Verify it's a callable method
        assert callable(getattr(BedrockClient, 'generate_prescription_data')), (
            "generate_prescription_data should be a callable method"
        )
    
    def test_bedrock_client_has_prompt_construction_method(self):
        """
        Test that BedrockClient has _construct_prompt method.
        
        EXPECTED: PASS on unfixed code (baseline behavior)
        """
        from aws_services.bedrock_client import BedrockClient
        
        assert hasattr(BedrockClient, '_construct_prompt'), (
            "BedrockClient missing _construct_prompt method"
        )
        
        # Verify it's a callable method
        assert callable(getattr(BedrockClient, '_construct_prompt')), (
            "_construct_prompt should be a callable method"
        )
    
    def test_bedrock_client_has_function_schema_builder(self):
        """
        Test that BedrockClient has _build_function_schema method.
        
        EXPECTED: PASS on unfixed code (baseline behavior)
        """
        from aws_services.bedrock_client import BedrockClient
        
        assert hasattr(BedrockClient, '_build_function_schema'), (
            "BedrockClient missing _build_function_schema method"
        )
        
        # Verify it's a callable method
        assert callable(getattr(BedrockClient, '_build_function_schema')), (
            "_build_function_schema should be a callable method"
        )
    
    def test_function_call_response_model_exists(self):
        """
        Test that FunctionCallResponse model is defined.
        
        EXPECTED: PASS on unfixed code (baseline behavior)
        """
        from models.bedrock_extraction import FunctionCallResponse
        
        # Verify it's a class
        assert isinstance(FunctionCallResponse, type), (
            "FunctionCallResponse should be a class"
        )
    
    def test_hospital_configuration_model_exists(self):
        """
        Test that HospitalConfiguration model is defined.
        
        EXPECTED: PASS on unfixed code (baseline behavior)
        """
        from models.bedrock_extraction import HospitalConfiguration
        
        # Verify it's a class
        assert isinstance(HospitalConfiguration, type), (
            "HospitalConfiguration should be a class"
        )


class TestPolicyJSONStructurePreservation:
    """
    Property-based tests for JSON structure preservation.
    
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
    
    These tests verify that the policy JSON structure is valid and consistent.
    """
    
    def test_policy_is_valid_json(self):
        """
        Test that the policy file is valid JSON.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy_path = 'seva-arogya-infra/iam_policies/bedrock_comprehend_policy.json'
        
        with open(policy_path, 'r') as f:
            content = f.read()
        
        # Should not raise JSONDecodeError
        policy = json.loads(content)
        
        assert isinstance(policy, dict), (
            "Policy should be a JSON object (dict)"
        )
    
    def test_policy_has_required_top_level_fields(self):
        """
        Test that the policy has required top-level fields.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        
        assert 'Version' in policy, "Policy missing 'Version' field"
        assert 'Statement' in policy, "Policy missing 'Statement' field"
        
        assert isinstance(policy['Statement'], list), (
            "Policy 'Statement' should be a list"
        )
    
    def test_policy_statements_are_objects(self):
        """
        Test that all policy statements are JSON objects.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        
        statements = policy.get('Statement', [])
        
        for i, statement in enumerate(statements):
            assert isinstance(statement, dict), (
                f"Statement {i} should be a JSON object (dict), found: {type(statement)}"
            )
    
    @settings(max_examples=20)
    @given(st.sampled_from(['ComprehendMedicalAccess', 'BedrockRuntimeAccess']))
    def test_statement_actions_are_lists(self, sid):
        """
        Property: All statement Action fields must be lists.
        
        EXPECTED: PASS on unfixed policy (baseline behavior)
        """
        policy = get_iam_policy()
        statement = get_policy_statement_by_sid(policy, sid)
        
        assert statement, f"Statement with Sid '{sid}' not found"
        
        actions = statement.get('Action')
        assert isinstance(actions, list), (
            f"Statement '{sid}' Action should be a list, found: {type(actions)}"
        )
        
        # All actions should be strings
        for action in actions:
            assert isinstance(action, str), (
                f"Action in '{sid}' should be string, found: {type(action)}"
            )
