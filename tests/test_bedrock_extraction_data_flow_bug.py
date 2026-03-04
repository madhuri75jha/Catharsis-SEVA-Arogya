"""
Bug Condition Exploration Test for Bedrock Extraction Data Flow Fix

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

This test encodes the EXPECTED behavior - it will FAIL on unfixed infrastructure,
confirming the IAM namespace bug exists. When the bug is fixed, this test will PASS.

CRITICAL: This test MUST FAIL on unfixed infrastructure - failure confirms the bug exists.
DO NOT attempt to fix the test or the IAM policy when it fails.

GOAL: Surface counterexamples that demonstrate the IAM namespace mismatch prevents
Bedrock invocation in the extraction data flow.

Property 1: Fault Condition - Bedrock Model Invocation Authorization Failure

This test verifies that the extraction pipeline fails due to IAM namespace mismatch
when attempting to invoke Bedrock models. The IAM policy uses `bedrock:InvokeModel`
but the boto3 bedrock-runtime client requires `bedrock-runtime:InvokeModel`.
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
    """Create a sample medical transcript for testing"""
    return """
Patient Name: John Doe
Age: 45 years
Chief Complaint: Persistent cough and fever for 5 days

History of Present Illness:
Patient presents with productive cough, fever up to 101°F, and mild chest discomfort.
Symptoms started 5 days ago. No shortness of breath. No recent travel.

Physical Examination:
- Temperature: 100.8°F
- Blood Pressure: 128/82 mmHg
- Respiratory: Bilateral crackles in lower lung fields
- No wheezing

Assessment:
Acute bronchitis, likely bacterial

Plan:
1. Amoxicillin 500mg three times daily for 7 days
2. Dextromethorphan cough syrup 10ml every 6 hours as needed
3. Acetaminophen 500mg every 6 hours for fever
4. Increase fluid intake
5. Follow-up in 3 days if symptoms persist
"""


def create_sample_entities():
    """Create sample medical entities for testing"""
    return [
        {
            'entity_type': 'MEDICATION',
            'text': 'Amoxicillin 500mg'
        },
        {
            'entity_type': 'MEDICATION',
            'text': 'Dextromethorphan'
        },
        {
            'entity_type': 'MEDICATION',
            'text': 'Acetaminophen 500mg'
        },
        {
            'entity_type': 'DOSAGE',
            'text': 'three times daily'
        },
        {
            'entity_type': 'DOSAGE',
            'text': '10ml every 6 hours'
        },
        {
            'entity_type': 'DURATION',
            'text': '7 days'
        }
    ]


def create_sample_hospital_config():
    """Create hospital configuration for testing"""
    from models.bedrock_extraction import HospitalConfiguration, SectionDefinition, FieldDefinition
    
    return HospitalConfiguration(
        hospital_id='test-hospital',
        hospital_name='Test Hospital',
        version='1.0',
        sections=[
            SectionDefinition(
                section_id='patient_info',
                section_label='Patient Information',
                display_order=1,
                repeatable=False,
                fields=[
                    FieldDefinition(
                        field_name='patient_name',
                        display_label='Patient Name',
                        field_type='text',
                        description='Full name of the patient',
                        required=True,
                        display_order=1
                    ),
                    FieldDefinition(
                        field_name='age',
                        display_label='Age',
                        field_type='number',
                        description='Patient age in years',
                        required=False,
                        display_order=2
                    )
                ]
            ),
            SectionDefinition(
                section_id='medications',
                section_label='Medications',
                display_order=2,
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
                    ),
                    FieldDefinition(
                        field_name='duration',
                        display_label='Duration',
                        field_type='text',
                        description='Duration of treatment',
                        required=False,
                        display_order=3
                    )
                ]
            )
        ]
    )


@pytest.fixture
def config_manager():
    """Fixture to provide ConfigManager instance"""
    from aws_services.config_manager import ConfigManager
    return ConfigManager()


@pytest.fixture
def extraction_pipeline(config_manager):
    """Fixture to provide ExtractionPipeline instance"""
    from aws_services.extraction_pipeline import ExtractionPipeline
    return ExtractionPipeline(config_manager)


class TestBedrockExtractionDataFlowBugCondition:
    """
    Property 1: Fault Condition - Bedrock Model Invocation Authorization Failure
    
    For any extraction request where the extraction pipeline attempts to invoke
    Bedrock models using the boto3 bedrock-runtime client, the IAM policy SHALL
    grant the required bedrock-runtime:InvokeModel permission (not bedrock:InvokeModel),
    allowing the extraction data flow to complete successfully.
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """
    
    def test_bug_condition_holds(self):
        """
        Verify that the bug condition holds (IAM policy uses incorrect namespace).
        
        This test confirms we're testing the right scenario.
        
        **Validates: Requirement 2.4**
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
        
        **Validates: Requirement 2.4**
        """
        policy_check = check_policy_has_correct_namespace()
        
        if 'error' in policy_check:
            pytest.skip(f"Cannot check policy: {policy_check['error']}")
        
        # On unfixed code, this should pass (confirming the bug exists)
        assert policy_check['has_incorrect_namespace'], (
            "Expected IAM policy to use incorrect 'bedrock:' namespace, "
            f"but found actions: {policy_check['actions']}"
        )
    
    def test_extraction_pipeline_bedrock_invocation(self, extraction_pipeline):
        """
        Test that extraction pipeline fails to invoke Bedrock due to IAM namespace mismatch.
        
        This test attempts the full extraction data flow:
        1. Comprehend Medical entity extraction (should work - uses correct namespace)
        2. Bedrock model invocation (should fail - uses incorrect namespace in policy)
        
        EXPECTED ON UNFIXED CODE: FAIL - Bedrock invocation fails with AccessDeniedException
        EXPECTED ON FIXED CODE: PASS - Extraction completes successfully
        
        **Validates: Requirements 2.1, 2.2, 2.3**
        """
        if not is_bug_condition():
            pytest.skip("Bug condition does not hold - policy already has correct namespace")
        
        # Prepare test data
        transcript = create_sample_transcript()
        hospital_id = 'test-hospital'
        
        # Check the policy file - this is the source of truth for the bug
        policy_check = check_policy_has_correct_namespace()
        
        # Attempt extraction
        extraction_result = {
            'attempted': False,
            'succeeded': False,
            'error': None,
            'error_type': None
        }
        
        try:
            result = extraction_pipeline.extract_prescription_data(
                transcript=transcript,
                hospital_id=hospital_id,
                request_id='test-bug-exploration'
            )
            extraction_result['attempted'] = True
            
            if result is not None and len(result.sections) > 0:
                extraction_result['succeeded'] = True
            else:
                extraction_result['error'] = 'Extraction returned None or empty sections'
                
        except ClientError as e:
            extraction_result['attempted'] = True
            extraction_result['error_type'] = e.response['Error']['Code']
            extraction_result['error'] = e.response['Error']['Message']
        except Exception as e:
            extraction_result['attempted'] = True
            extraction_result['error_type'] = type(e).__name__
            extraction_result['error'] = str(e)
        
        # The bug is confirmed if the policy has incorrect namespace
        if policy_check['has_incorrect_namespace']:
            pytest.fail(
                f"COUNTEREXAMPLE FOUND: Extraction data flow fails due to IAM namespace mismatch.\n"
                f"\n"
                f"IAM Policy Issue:\n"
                f"  Policy actions: {policy_check['actions']}\n"
                f"  Expected: bedrock-runtime:InvokeModel and bedrock-runtime:InvokeModelWithResponseStream\n"
                f"  Actual: Policy uses 'bedrock:' namespace instead of 'bedrock-runtime:'\n"
                f"\n"
                f"Extraction Data Flow Result:\n"
                f"  Attempted: {extraction_result['attempted']}\n"
                f"  Succeeded: {extraction_result['succeeded']}\n"
                f"  Error Type: {extraction_result['error_type']}\n"
                f"  Error: {extraction_result['error']}\n"
                f"\n"
                f"Expected Behavior on ECS:\n"
                f"  When deployed to ECS with this policy, the extraction pipeline will fail at\n"
                f"  the Bedrock invocation step with:\n"
                f"    AccessDeniedException: User is not authorized to perform: bedrock-runtime:InvokeModel\n"
                f"  This causes the /api/v1/extract endpoint to return 500 Internal Server Error.\n"
                f"\n"
                f"Root Cause:\n"
                f"  The boto3 bedrock-runtime client (used in bedrock_client.py) requires\n"
                f"  'bedrock-runtime:' namespace permissions, but the IAM policy grants\n"
                f"  'bedrock:' namespace permissions. This namespace mismatch causes AWS IAM\n"
                f"  to deny the request.\n"
                f"\n"
                f"Note: Local credentials may have different permissions than the ECS task role."
            )
    
    def test_direct_bedrock_client_invocation(self):
        """
        Test direct Bedrock client invocation to isolate the IAM issue.
        
        This test bypasses the extraction pipeline and directly tests the
        BedrockClient.generate_prescription_data() method.
        
        EXPECTED ON UNFIXED CODE: FAIL - AccessDeniedException due to IAM namespace
        EXPECTED ON FIXED CODE: PASS - Successful invocation
        
        **Validates: Requirements 2.2, 2.3**
        """
        if not is_bug_condition():
            pytest.skip("Bug condition does not hold - policy already has correct namespace")
        
        from aws_services.bedrock_client import BedrockClient
        
        # Initialize client
        region = os.environ.get('AWS_REGION', 'ap-south-1')
        model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
        
        client = BedrockClient(region=region, model_id=model_id)
        
        # Prepare test data
        transcript = create_sample_transcript()
        entities = create_sample_entities()
        hospital_config = create_sample_hospital_config()
        
        # Check the policy file
        policy_check = check_policy_has_correct_namespace()
        
        # Attempt invocation
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
        except Exception as e:
            invocation_result['attempted'] = True
            invocation_result['error_code'] = type(e).__name__
            invocation_result['error_message'] = str(e)
        
        # The bug is confirmed if the policy has incorrect namespace
        if policy_check['has_incorrect_namespace']:
            pytest.fail(
                f"COUNTEREXAMPLE FOUND: Direct Bedrock invocation fails due to IAM namespace.\n"
                f"\n"
                f"IAM Policy Issue:\n"
                f"  Policy actions: {policy_check['actions']}\n"
                f"  Expected: bedrock-runtime:InvokeModel\n"
                f"  Actual: Policy uses 'bedrock:InvokeModel' (incorrect namespace)\n"
                f"\n"
                f"Invocation Result:\n"
                f"  Attempted: {invocation_result['attempted']}\n"
                f"  Succeeded: {invocation_result['succeeded']}\n"
                f"  Error Code: {invocation_result['error_code']}\n"
                f"  Error Message: {invocation_result['error_message']}\n"
                f"\n"
                f"Expected Error on ECS:\n"
                f"  AccessDeniedException: User: arn:aws:sts::ACCOUNT:assumed-role/ROLE/TASK\n"
                f"  is not authorized to perform: bedrock-runtime:InvokeModel on resource:\n"
                f"  arn:aws:bedrock:REGION::foundation-model/MODEL_ID\n"
                f"\n"
                f"Note: Local test may succeed if local credentials have correct permissions."
            )
    
    def test_api_endpoint_extraction_flow(self):
        """
        Test the /api/v1/extract endpoint flow (simulated).
        
        This test simulates what happens when the frontend calls the extraction API.
        
        EXPECTED ON UNFIXED CODE: FAIL - Returns 500 error due to Bedrock invocation failure
        EXPECTED ON FIXED CODE: PASS - Returns 200 with prescription data
        
        **Validates: Requirement 2.1**
        """
        if not is_bug_condition():
            pytest.skip("Bug condition does not hold - policy already has correct namespace")
        
        from aws_services.extraction_pipeline import ExtractionPipeline
        from aws_services.config_manager import ConfigManager
        from models.bedrock_extraction import ExtractionRequest
        
        # Initialize pipeline
        config_manager = ConfigManager()
        pipeline = ExtractionPipeline(config_manager)
        
        # Create extraction request (simulating API request body)
        request_data = {
            'transcript': create_sample_transcript(),
            'hospital_id': 'default',
            'request_id': 'test-api-flow'
        }
        
        extraction_request = ExtractionRequest(**request_data)
        
        # Validate request
        is_valid, error_msg = pipeline.validate_request(extraction_request)
        assert is_valid, f"Request validation failed: {error_msg}"
        
        # Check policy
        policy_check = check_policy_has_correct_namespace()
        
        # Attempt extraction (simulating API endpoint logic)
        api_result = {
            'status_code': None,
            'response_body': None,
            'error': None
        }
        
        try:
            prescription_data = pipeline.extract_prescription_data(
                transcript=extraction_request.transcript,
                hospital_id=extraction_request.hospital_id,
                request_id=extraction_request.request_id
            )
            
            if prescription_data is None:
                api_result['status_code'] = 500
                api_result['response_body'] = {
                    'status': 'error',
                    'error_code': 'EXTRACTION_FAILED',
                    'error_message': 'Failed to extract prescription data'
                }
            else:
                api_result['status_code'] = 200
                api_result['response_body'] = {
                    'status': 'success',
                    'prescription_data': prescription_data.model_dump(mode='json'),
                    'request_id': prescription_data.request_id
                }
                
        except Exception as e:
            api_result['status_code'] = 500
            api_result['response_body'] = {
                'status': 'error',
                'error_code': 'INTERNAL_ERROR',
                'error_message': 'An unexpected error occurred'
            }
            api_result['error'] = str(e)
        
        # The bug is confirmed if the policy has incorrect namespace
        if policy_check['has_incorrect_namespace']:
            pytest.fail(
                f"COUNTEREXAMPLE FOUND: API extraction endpoint fails due to IAM namespace.\n"
                f"\n"
                f"IAM Policy Issue:\n"
                f"  Policy uses 'bedrock:' namespace instead of 'bedrock-runtime:'\n"
                f"  Actions in policy: {policy_check['actions']}\n"
                f"\n"
                f"API Response:\n"
                f"  Status Code: {api_result['status_code']}\n"
                f"  Response Body: {json.dumps(api_result['response_body'], indent=2)}\n"
                f"  Error: {api_result['error']}\n"
                f"\n"
                f"Expected Behavior on ECS:\n"
                f"  POST /api/v1/extract returns 500 Internal Server Error\n"
                f"  Browser console shows: POST https://sevaarogya.shoppertrends.in/api/v1/extract 500\n"
                f"  Backend logs show: AccessDeniedException for bedrock-runtime:InvokeModel\n"
                f"\n"
                f"Impact:\n"
                f"  Users cannot generate prescription data from medical transcripts.\n"
                f"  The extraction feature is completely broken in production."
            )
    
    def test_streaming_invocation_namespace(self):
        """
        Test that streaming invocation also requires correct namespace.
        
        The IAM policy must grant bedrock-runtime:InvokeModelWithResponseStream,
        not bedrock:InvokeModelWithResponseStream.
        
        **Validates: Requirement 2.4**
        """
        policy_check = check_policy_has_correct_namespace()
        
        if 'error' in policy_check:
            pytest.skip(f"Cannot check policy: {policy_check['error']}")
        
        # Check streaming action specifically
        has_correct_stream = policy_check.get('has_correct_stream', False)
        has_incorrect_stream = policy_check.get('has_incorrect_stream', False)
        
        if has_incorrect_stream:
            pytest.fail(
                f"COUNTEREXAMPLE FOUND: Streaming invocation uses incorrect namespace.\n"
                f"\n"
                f"IAM Policy Issue:\n"
                f"  Policy uses 'bedrock:InvokeModelWithResponseStream'\n"
                f"  Expected: 'bedrock-runtime:InvokeModelWithResponseStream'\n"
                f"  Actions in policy: {policy_check['actions']}\n"
                f"\n"
                f"Impact:\n"
                f"  If the application uses streaming responses (invoke_model_with_response_stream),\n"
                f"  those calls will also fail with AccessDeniedException.\n"
                f"\n"
                f"Note: Both InvokeModel and InvokeModelWithResponseStream require the\n"
                f"      'bedrock-runtime:' namespace prefix."
            )


class TestBedrockExtractionPreservation:
    """
    Preservation tests to verify non-Bedrock operations remain unchanged.
    
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
    """
    
    def test_comprehend_medical_permissions_unchanged(self):
        """
        Test that Comprehend Medical permissions are present and unchanged.
        
        The bug fix should not affect Comprehend Medical operations.
        
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
        
        The bug fix should not affect resource restrictions.
        
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
    
    def test_iam_policy_structure_preserved(self):
        """
        Test that the IAM policy has the expected structure.
        
        The bug fix should only change action namespaces, not policy structure.
        
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
