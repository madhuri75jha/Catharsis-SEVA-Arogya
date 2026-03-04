"""
Preservation Property Tests for Bedrock Extraction Data Flow Fix

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

These tests capture the CURRENT behavior of non-Bedrock operations on UNFIXED
infrastructure to ensure they are preserved after the IAM namespace fix.

EXPECTED OUTCOME: Tests PASS on unfixed infrastructure (confirms baseline behavior)
"""
import pytest
import json
import os


def get_iam_policy():
    """Load the IAM policy from the JSON file."""
    policy_path = 'seva-arogya-infra/iam_policies/bedrock_comprehend_policy.json'
    try:
        with open(policy_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None


class TestComprehendMedicalPreservation:
    """Test that Comprehend Medical permissions are preserved - Requirement 3.1"""
    
    def test_comprehend_medical_permissions_in_policy(self):
        """Verify Comprehend Medical permissions are present in IAM policy"""
        policy = get_iam_policy()
        if not policy:
            pytest.skip("IAM policy file not found")
        
        comprehend_statement = None
        for statement in policy.get('Statement', []):
            if statement.get('Sid') == 'ComprehendMedicalAccess':
                comprehend_statement = statement
                break
        
        assert comprehend_statement is not None, "ComprehendMedicalAccess statement not found"
        
        actions = comprehend_statement.get('Action', [])
        expected_actions = [
            'comprehendmedical:DetectEntitiesV2',
            'comprehendmedical:InferICD10CM',
            'comprehendmedical:InferRxNorm'
        ]
        
        for expected_action in expected_actions:
            assert expected_action in actions, f"Missing action: {expected_action}"
        
        assert comprehend_statement.get('Effect') == 'Allow'
        assert comprehend_statement.get('Resource') == '*'


class TestBedrockResourceRestrictionsPreservation:
    """Test that Bedrock resource restrictions are preserved - Requirement 3.2"""
    
    def test_bedrock_resource_restrictions_present(self):
        """Verify Bedrock resource ARNs restrict access to Claude 3 models only"""
        policy = get_iam_policy()
        if not policy:
            pytest.skip("IAM policy file not found")
        
        bedrock_statement = None
        for statement in policy.get('Statement', []):
            if statement.get('Sid') == 'BedrockRuntimeAccess':
                bedrock_statement = statement
                break
        
        assert bedrock_statement is not None, "BedrockRuntimeAccess statement not found"
        
        resources = bedrock_statement.get('Resource', [])
        assert len(resources) > 0, "BedrockRuntimeAccess must have specific resource ARNs"
        
        for resource in resources:
            assert 'anthropic.claude-3' in resource, f"Resource not Claude 3: {resource}"
            assert resource.startswith('arn:aws:bedrock:')
            assert 'foundation-model' in resource
    
    def test_bedrock_policy_structure_preserved(self):
        """Verify IAM policy structure is preserved"""
        policy = get_iam_policy()
        if not policy:
            pytest.skip("IAM policy file not found")
        
        assert policy.get('Version') == '2012-10-17'
        
        statements = policy.get('Statement', [])
        assert len(statements) == 2, f"Expected 2 statements, found {len(statements)}"
        
        sids = [stmt.get('Sid') for stmt in statements]
        assert 'ComprehendMedicalAccess' in sids
        assert 'BedrockRuntimeAccess' in sids
        
        for statement in statements:
            assert statement.get('Effect') == 'Allow'
    
    def test_streaming_invocation_permission_present(self):
        """Verify streaming invocation permission is present - Requirement 3.3"""
        policy = get_iam_policy()
        if not policy:
            pytest.skip("IAM policy file not found")
        
        bedrock_statement = None
        for statement in policy.get('Statement', []):
            if statement.get('Sid') == 'BedrockRuntimeAccess':
                bedrock_statement = statement
                break
        
        assert bedrock_statement is not None
        
        actions = bedrock_statement.get('Action', [])
        has_streaming = any('InvokeModelWithResponseStream' in action for action in actions)
        
        assert has_streaming, "InvokeModelWithResponseStream action must be present"


class TestRetryLogicPreservation:
    """Test that retry logic is preserved - Requirement 3.5"""
    
    def test_comprehend_retry_configuration(self):
        """Verify ComprehendManager has retry configuration"""
        from aws_services.comprehend_manager import ComprehendManager
        
        region = os.environ.get('AWS_COMPREHEND_REGION', os.environ.get('AWS_REGION', 'ap-south-1'))
        comprehend_manager = ComprehendManager(region=region)
        
        assert hasattr(comprehend_manager, 'MAX_RETRIES')
        assert hasattr(comprehend_manager, 'RETRY_DELAYS')
        assert comprehend_manager.MAX_RETRIES == 3
        assert comprehend_manager.RETRY_DELAYS == [1.0, 2.0, 4.0]
    
    def test_bedrock_retry_configuration(self):
        """Verify BedrockClient has retry configuration"""
        from aws_services.bedrock_client import BedrockClient
        
        region = os.environ.get('BEDROCK_REGION', 'us-east-1')
        model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
        
        bedrock_client = BedrockClient(region=region, model_id=model_id)
        
        assert hasattr(bedrock_client, 'MAX_RETRIES')
        assert hasattr(bedrock_client, 'RETRY_DELAYS')
        assert bedrock_client.MAX_RETRIES == 3
        assert bedrock_client.RETRY_DELAYS == [1.0, 2.0, 4.0]


class TestExtractionPipelineStructurePreservation:
    """Test that extraction pipeline structure is preserved - Requirement 3.4"""
    
    def test_extraction_pipeline_initialization(self):
        """Verify ExtractionPipeline initializes correctly"""
        from aws_services.config_manager import ConfigManager
        from aws_services.extraction_pipeline import ExtractionPipeline
        
        config_manager = ConfigManager()
        pipeline = ExtractionPipeline(config_manager)
        
        assert hasattr(pipeline, 'comprehend_manager')
        assert hasattr(pipeline, 'bedrock_client')
        assert hasattr(pipeline, 'validation_layer')
        assert hasattr(pipeline, 'config_manager')
    
    def test_validation_layer_exists(self):
        """Verify ValidationLayer has expected methods"""
        from aws_services.validation_layer import ValidationLayer
        
        validation_layer = ValidationLayer()
        
        assert hasattr(validation_layer, 'validate_function_call')
        assert hasattr(validation_layer, 'format_prescription_data')
        assert callable(validation_layer.validate_function_call)
        assert callable(validation_layer.format_prescription_data)


class TestConfigurationManagementPreservation:
    """Test that configuration management is preserved - Requirement 3.6"""
    
    def test_config_manager_initialization(self):
        """Verify ConfigManager initializes correctly"""
        from aws_services.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        
        assert config_manager.get('aws_region') is not None
        assert config_manager.get('bedrock_region') is not None
        assert config_manager.get('bedrock_model_id') is not None
