"""
Bug Condition Exploration Test for Bedrock IAM Permissions Fix

**Validates: Requirements 2.1, 2.2, 2.3**

This test encodes the EXPECTED behavior - it will FAIL on unfixed code,
confirming the bug exists. When the bug is fixed, this test will PASS.

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

GOAL: Surface counterexamples that demonstrate the IAM namespace bug exists.

This test verifies that the IAM policy authorizes bedrock-runtime:InvokeModel
and bedrock-runtime:InvokeModelWithResponseStream actions by attempting to
invoke Bedrock models using the actual bedrock_client.
"""
import pytest
import json
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_iam_policy():
    """
    Load the IAM policy from the JSON file.
    
    Returns dict with policy content or None if file not found.
    """
    policy_path = 'seva-arogya-infra/iam_policies/bedrock_comprehend_policy.json'
    try:
        with open(policy_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def check_policy_has_correct_namespace():
    """
    Check if the IAM policy uses the correct bedrock-runtime namespace.
    
    Returns dict with:
    - has_correct_namespace: bool - whether policy uses bedrock-runtime:InvokeModel
    - has_incorrect_namespace: bool - whether policy uses bedrock:InvokeModel
    - actions: list of actions in BedrockRuntimeAccess statement
    """
    policy = get_iam_policy()
    
    if not policy:
        return {
            'has_correct_namespace': False,
            'has_incorrect_namespace': False,
            'actions': [],
            'error': 'Policy file not found'
        }
    
    # Find BedrockRuntimeAccess statement
    bedrock_statement = None
    for statement in policy.get('Statement', []):
        if statement.get('Sid') == 'BedrockRuntimeAccess':
            bedrock_statement = statement
            break
    
    if not bedrock_statement:
        return {
            'has_correct_namespace': False,
            'has_incorrect_namespace': False,
            'actions': [],
            'error': 'BedrockRuntimeAccess statement not found'
        }
    
    actions = bedrock_statement.get('Action', [])
    
    # Check for correct namespace (bedrock-runtime:)
    has_correct_invoke = 'bedrock-runtime:InvokeModel' in actions
    has_correct_stream = 'bedrock-runtime:InvokeModelWithResponseStream' in actions
    
    # Check for incorrect namespace (bedrock:)
    has_incorrect_invoke = 'bedrock:InvokeModel' in actions
    has_incorrect_stream = 'bedrock:InvokeModelWithResponseStream' in actions
    
    return {
        'has_correct_namespace': has_correct_invoke and has_correct_stream,
        'has_incorrect_namespace': has_incorrect_invoke or has_incorrect_stream,
        'actions': actions,
        'has_correct_invoke': has_correct_invoke,
        'has_correct_stream': has_correct_stream,
        'has_incorrect_invoke': has_incorrect_invoke,
        'has_incorrect_stream': has_incorrect_stream
    }


def is_bug_condition():
    """
    Check if the bug condition holds (IAM policy uses incorrect bedrock: namespace).
    
    Returns True if the policy uses bedrock: instead of bedrock-runtime:.
    """
    policy_check = check_policy_has_correct_namespace()
    
    # Bug exists if policy has incorrect namespace
    return policy_check.get('has_incorrect_namespace', False)


def create_sample_transcript():
    """Create a minimal sample transcript for testing"""
    return """
    Patient: John Doe
    Chief Complaint: Fever and cough for 3 days
    Diagnosis: Upper respiratory tract infection
    Prescription: Amoxicillin 500mg, take 3 times daily for 7 days
    """


def create_sample_entities():
    """Create minimal sample entities for testing"""
    return [
        {
            'entity_type': 'MEDICATION',
            'text': 'Amoxicillin 500mg'
        },
        {
            'entity_type': 'DOSAGE',
            'text': '3 times daily'
        }
    ]


def create_sample_hospital_config():
    """Create minimal hospital configuration for testing"""
    from models.bedrock_extraction import HospitalConfiguration, SectionDefinition, FieldDefinition
    
    return HospitalConfiguration(
        hospital_id='test-hospital',
        hospital_name='Test Hospital',
        version='1.0',
        sections=[
            SectionDefinition(
                section_id='medications',
                section_label='Medications',
                display_order=1,
                repeatable=True,
                fields=[
                    FieldDefinition(
                        field_name='medication_name',
                        display_label='Medication Name',
                        field_type='text',
                        description='Name of the medication',
                        required=True,
                        display_order=1
                    ),
                    FieldDefinition(
                        field_name='dosage',
                        display_label='Dosage',
                        field_type='text',
                        description='Dosage instructions',
                        required=False,
                        display_order=2
                    )
                ]
            )
        ]
    )


@pytest.fixture
def bedrock_config():
    """Fixture to provide Bedrock configuration from environment"""
    return {
        'region': os.environ.get('AWS_REGION', 'ap-south-1'),
        'model_id': os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
    }


class TestBedrockIAMBugCondition:
    """
    Property 1: Fault Condition - Bedrock Model Invocation Authorization
    
    For any IAM policy action where the action is intended for Bedrock Runtime
    model invocation (InvokeModel or InvokeModelWithResponseStream), the fixed
    IAM policy SHALL use the bedrock-runtime: namespace prefix, enabling
    successful authorization when the boto3 bedrock-runtime client invokes models.
    
    **Validates: Requirements 2.1, 2.2, 2.3**
    """
    
    def test_bug_condition_holds(self):
        """
        Verify that the bug condition holds (IAM policy uses incorrect namespace).
        
        This test confirms we're testing the right scenario.
        """
        policy_check = check_policy_has_correct_namespace()
        
        if 'error' in policy_check:
            pytest.skip(f"Cannot verify bug condition: {policy_check['error']}")
        
        # Bug condition: policy should have incorrect namespace before fix
        assert policy_check['has_incorrect_namespace'], (
            "Bug condition does not hold: IAM policy already uses correct namespace. "
            f"Actions in policy: {policy_check['actions']}"
        )
    
    def test_iam_policy_uses_incorrect_namespace(self):
        """
        Test that the IAM policy currently uses bedrock: instead of bedrock-runtime:.
        
        EXPECTED ON UNFIXED CODE: PASS - confirms policy has incorrect namespace
        EXPECTED ON FIXED CODE: FAIL - policy should have correct namespace
        
        This test documents the current buggy state.
        
        **Validates: Requirement 2.3**
        """
        policy_check = check_policy_has_correct_namespace()
        
        if 'error' in policy_check:
            pytest.skip(f"Cannot check policy: {policy_check['error']}")
        
        # On unfixed code, this should pass (confirming the bug exists)
        assert policy_check['has_incorrect_namespace'], (
            "Expected IAM policy to use incorrect 'bedrock:' namespace, "
            f"but found actions: {policy_check['actions']}"
        )
    
    def test_iam_policy_missing_correct_namespace(self):
        """
        Test that the IAM policy does NOT have the correct bedrock-runtime: namespace.
        
        EXPECTED ON UNFIXED CODE: PASS - confirms policy lacks correct namespace
        EXPECTED ON FIXED CODE: FAIL - policy should have correct namespace
        
        **Validates: Requirement 2.3**
        """
        policy_check = check_policy_has_correct_namespace()
        
        if 'error' in policy_check:
            pytest.skip(f"Cannot check policy: {policy_check['error']}")
        
        # On unfixed code, this should pass (confirming the bug exists)
        assert not policy_check['has_correct_namespace'], (
            "Expected IAM policy to be missing 'bedrock-runtime:' namespace, "
            f"but found actions: {policy_check['actions']}"
        )
    
    def test_bedrock_client_initialization_succeeds(self, bedrock_config):
        """
        Test that BedrockClient can be initialized (this should work regardless of IAM).
        
        This verifies the client setup is correct before testing invocation.
        
        **Validates: Requirement 2.1**
        """
        from aws_services.bedrock_client import BedrockClient
        
        # Client initialization should succeed (doesn't require IAM permissions)
        client = BedrockClient(
            region=bedrock_config['region'],
            model_id=bedrock_config['model_id']
        )
        
        assert client is not None
        assert client.model_id == bedrock_config['model_id']
    
    def test_bedrock_invocation_with_policy_check(self, bedrock_config):
        """
        Test Bedrock invocation and verify IAM policy namespace.
        
        This test verifies the bug exists by checking the IAM policy file.
        When deployed to ECS with the buggy policy, invocations would fail with
        AccessDeniedException. Locally, we may have different credentials.
        
        EXPECTED ON UNFIXED CODE: FAIL - Policy has incorrect namespace
        EXPECTED ON FIXED CODE: PASS - Policy has correct namespace
        
        **Validates: Requirements 2.1, 2.2, 2.3**
        """
        if not is_bug_condition():
            pytest.skip("Bug condition does not hold - policy already has correct namespace")
        
        from aws_services.bedrock_client import BedrockClient
        
        # Initialize client
        client = BedrockClient(
            region=bedrock_config['region'],
            model_id=bedrock_config['model_id']
        )
        
        # Prepare test data
        transcript = create_sample_transcript()
        entities = create_sample_entities()
        hospital_config = create_sample_hospital_config()
        
        # Check the policy file - this is the source of truth for the bug
        policy_check = check_policy_has_correct_namespace()
        
        # Attempt to invoke Bedrock
        invocation_result = {
            'attempted': False,
            'succeeded': False,
            'error_code': None,
            'error_message': None
        }
        
        try:
            result = client.generate_prescription_data(
                transcript=transcript,
                entities=entities,
                hospital_config=hospital_config
            )
            invocation_result['attempted'] = True
            invocation_result['succeeded'] = True
            
        except ClientError as e:
            invocation_result['attempted'] = True
            invocation_result['error_code'] = e.response['Error']['Code']
            invocation_result['error_message'] = e.response['Error']['Message']
        
        # The bug is confirmed if the policy has incorrect namespace
        # The invocation result depends on which credentials are used locally
        if policy_check['has_incorrect_namespace']:
            pytest.fail(
                f"COUNTEREXAMPLE FOUND: IAM policy uses incorrect namespace.\n"
                f"Policy actions: {policy_check['actions']}\n"
                f"Expected: bedrock-runtime:InvokeModel and bedrock-runtime:InvokeModelWithResponseStream\n"
                f"Actual: Policy uses 'bedrock:' namespace instead of 'bedrock-runtime:'\n"
                f"\n"
                f"When deployed to ECS with this policy, Bedrock invocations will fail with:\n"
                f"  AccessDeniedException: User is not authorized to perform: bedrock-runtime:InvokeModel\n"
                f"\n"
                f"Local invocation result (may differ due to different credentials):\n"
                f"  Attempted: {invocation_result['attempted']}\n"
                f"  Succeeded: {invocation_result['succeeded']}\n"
                f"  Error: {invocation_result['error_code']} - {invocation_result['error_message']}\n"
                f"\n"
                f"Note: Local credentials may have correct permissions even though the policy file is buggy."
            )
    
    def test_iam_policy_structure_preserved(self):
        """
        Test that the IAM policy has the expected structure (2 statements, correct Sids).
        
        This verifies the policy file is in the expected format before testing the fix.
        
        **Validates: Requirement 3.2**
        """
        policy = get_iam_policy()
        
        if not policy:
            pytest.skip("IAM policy file not found")
        
        statements = policy.get('Statement', [])
        
        # Should have exactly 2 statements
        assert len(statements) == 2, (
            f"Expected 2 statements in IAM policy, found {len(statements)}"
        )
        
        # Check statement Sids
        sids = [stmt.get('Sid') for stmt in statements]
        assert 'ComprehendMedicalAccess' in sids, "Missing ComprehendMedicalAccess statement"
        assert 'BedrockRuntimeAccess' in sids, "Missing BedrockRuntimeAccess statement"
    
    def test_comprehend_medical_permissions_unchanged(self):
        """
        Test that Comprehend Medical permissions are present and unchanged.
        
        This verifies that the bug fix won't affect Comprehend Medical permissions.
        
        **Validates: Requirement 3.1**
        """
        policy = get_iam_policy()
        
        if not policy:
            pytest.skip("IAM policy file not found")
        
        # Find ComprehendMedicalAccess statement
        comprehend_statement = None
        for statement in policy.get('Statement', []):
            if statement.get('Sid') == 'ComprehendMedicalAccess':
                comprehend_statement = statement
                break
        
        assert comprehend_statement is not None, "ComprehendMedicalAccess statement not found"
        
        # Verify expected actions
        actions = comprehend_statement.get('Action', [])
        expected_actions = [
            'comprehendmedical:DetectEntitiesV2',
            'comprehendmedical:InferICD10CM',
            'comprehendmedical:InferRxNorm'
        ]
        
        for expected_action in expected_actions:
            assert expected_action in actions, (
                f"Expected action '{expected_action}' not found in ComprehendMedicalAccess"
            )
    
    def test_bedrock_resource_restrictions_present(self):
        """
        Test that Bedrock resource restrictions (Claude 3 models) are present.
        
        This verifies that the bug fix won't affect resource restrictions.
        
        **Validates: Requirement 3.2**
        """
        policy = get_iam_policy()
        
        if not policy:
            pytest.skip("IAM policy file not found")
        
        # Find BedrockRuntimeAccess statement
        bedrock_statement = None
        for statement in policy.get('Statement', []):
            if statement.get('Sid') == 'BedrockRuntimeAccess':
                bedrock_statement = statement
                break
        
        assert bedrock_statement is not None, "BedrockRuntimeAccess statement not found"
        
        # Verify resources are restricted to Claude 3 models
        resources = bedrock_statement.get('Resource', [])
        assert len(resources) > 0, "No resources specified in BedrockRuntimeAccess"
        
        # All resources should be Claude 3 model ARNs
        for resource in resources:
            assert 'anthropic.claude-3' in resource, (
                f"Resource '{resource}' is not a Claude 3 model ARN"
            )


class TestBedrockIAMPropertyBased:
    """
    Property-based test to verify the IAM namespace bug affects all
    Bedrock Runtime operations.
    
    **Validates: Requirements 2.1, 2.2, 2.3**
    """
    
    def test_policy_namespace_consistency(self):
        """
        Property: All Bedrock Runtime actions in the policy must use the same namespace.
        
        On unfixed code: All actions use incorrect 'bedrock:' namespace
        On fixed code: All actions use correct 'bedrock-runtime:' namespace
        
        **Validates: Requirement 2.3**
        """
        policy_check = check_policy_has_correct_namespace()
        
        if 'error' in policy_check:
            pytest.skip(f"Cannot check policy: {policy_check['error']}")
        
        actions = policy_check['actions']
        
        # Extract namespaces from actions
        namespaces = set()
        for action in actions:
            if ':' in action:
                namespace = action.split(':')[0]
                namespaces.add(namespace)
        
        # All Bedrock actions should use the same namespace
        assert len(namespaces) <= 1, (
            f"Inconsistent namespaces in BedrockRuntimeAccess actions: {namespaces}. "
            f"All actions should use the same namespace (either 'bedrock' or 'bedrock-runtime')."
        )
        
        # On unfixed code, namespace should be 'bedrock' (incorrect)
        # On fixed code, namespace should be 'bedrock-runtime' (correct)
        if len(namespaces) == 1:
            namespace = list(namespaces)[0]
            
            # Document which namespace is currently used
            if namespace == 'bedrock':
                # This is the buggy state
                assert policy_check['has_incorrect_namespace'], (
                    "Policy uses 'bedrock' namespace but check says it's correct"
                )
            elif namespace == 'bedrock-runtime':
                # This is the fixed state
                assert policy_check['has_correct_namespace'], (
                    "Policy uses 'bedrock-runtime' namespace but check says it's incorrect"
                )
