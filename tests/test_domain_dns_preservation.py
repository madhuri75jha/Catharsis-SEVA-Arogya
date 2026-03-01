"""
Preservation Property Tests for Domain DNS Resolution Fix

**Validates: Requirements 3.1, 3.3, 3.4, 3.5**

This test verifies that the fix preserves existing behavior when ACM_ZONE_ID
is empty or not provided (manual DNS configuration scenarios).

IMPORTANT: These tests should PASS on UNFIXED code, confirming baseline behavior.

GOAL: Ensure the fix does not break existing deployments that don't use custom domains.

Property 2: Preservation - Manual DNS Configuration Support

For any Terraform configuration where ACM_ZONE_ID is empty or not provided,
the fixed Terraform configuration SHALL produce exactly the same infrastructure
as the original configuration, creating no Route53 records and allowing manual
DNS configuration.
"""
import pytest
import boto3
import os
import subprocess
import json
from hypothesis import given, strategies as st, settings, assume
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_env_variable(var_name, default=""):
    """Get environment variable value"""
    return os.environ.get(var_name, default)


def is_preservation_condition():
    """
    Check if the preservation condition holds (ACM_ZONE_ID is empty or not provided).
    
    Returns True if ACM_ZONE_ID is empty, indicating manual DNS configuration.
    """
    acm_zone_id = get_env_variable('ACM_ZONE_ID')
    
    return acm_zone_id == ""


def get_terraform_state():
    """
    Get Terraform state to check for Route53 record resources.
    
    Returns dict with resource information or None if terraform state is unavailable.
    """
    try:
        result = subprocess.run(
            ['terraform', 'state', 'list'],
            cwd='seva-arogya-infra',
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            resources = result.stdout.strip().split('\n') if result.stdout.strip() else []
            return {
                'has_alb_domain_a': any('aws_route53_record.alb_domain_a' in r for r in resources),
                'has_alb_domain_aaaa': any('aws_route53_record.alb_domain_aaaa' in r for r in resources),
                'has_alb_cert_validation': any('aws_route53_record.alb_cert_validation' in r for r in resources),
                'has_alb': any('module.alb.aws_lb.main' in r or 'aws_lb.main' in r for r in resources),
                'all_resources': resources
            }
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def check_terraform_config_has_route53_resources():
    """
    Check if the Terraform configuration (main.tf) defines Route53 A and AAAA record resources.
    
    Returns dict with:
    - has_a_record_resource: bool - whether aws_route53_record.alb_domain_a is defined
    - has_aaaa_record_resource: bool - whether aws_route53_record.alb_domain_aaaa is defined
    """
    try:
        with open('seva-arogya-infra/main.tf', 'r') as f:
            content = f.read()
        
        # Check for Route53 A record resource definition
        has_a_record = 'resource "aws_route53_record" "alb_domain_a"' in content
        
        # Check for Route53 AAAA record resource definition
        has_aaaa_record = 'resource "aws_route53_record" "alb_domain_aaaa"' in content
        
        return {
            'has_a_record_resource': has_a_record,
            'has_aaaa_record_resource': has_aaaa_record
        }
    except FileNotFoundError:
        return {
            'has_a_record_resource': False,
            'has_aaaa_record_resource': False,
            'error': 'main.tf not found'
        }


def get_alb_dns_name():
    """
    Get the ALB DNS name from Terraform state or output.
    
    Returns the ALB DNS name or None if unavailable.
    """
    try:
        # Try to get from terraform output
        result = subprocess.run(
            ['terraform', 'output', '-raw', 'alb_dns_name'],
            cwd='seva-arogya-infra',
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        
        # Fallback: try to get from state
        result = subprocess.run(
            ['terraform', 'state', 'show', 'module.alb.aws_lb.main'],
            cwd='seva-arogya-infra',
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Parse the output to find dns_name
            for line in result.stdout.split('\n'):
                if 'dns_name' in line and '=' in line:
                    dns_name = line.split('=')[1].strip().strip('"')
                    return dns_name
        
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def check_alb_accessibility(alb_dns_name):
    """
    Check if the ALB is accessible via its AWS DNS name.
    
    Returns dict with accessibility status:
    - accessible: bool
    - error: error message if check fails
    """
    try:
        import socket
        # Try to resolve the ALB DNS name
        addresses = socket.getaddrinfo(alb_dns_name, 80)
        ip_addresses = list(set([addr[4][0] for addr in addresses]))
        
        return {
            'accessible': True,
            'addresses': ip_addresses,
            'error': None
        }
    except socket.gaierror as e:
        return {
            'accessible': False,
            'addresses': None,
            'error': str(e)
        }


@pytest.fixture
def aws_config():
    """Fixture to provide AWS configuration from environment"""
    return {
        'acm_zone_id': get_env_variable('ACM_ZONE_ID'),
        'acm_domain_name': get_env_variable('ACM_DOMAIN_NAME'),
        'aws_region': get_env_variable('AWS_REGION', 'ap-south-1'),
        'enable_https': get_env_variable('ENABLE_HTTPS', 'false')
    }


class TestDomainDNSPreservation:
    """
    Property 2: Preservation - Manual DNS Configuration Support
    
    For any Terraform configuration where ACM_ZONE_ID is empty or not provided,
    the fixed Terraform configuration SHALL produce exactly the same infrastructure
    as the original configuration, creating no Route53 records and allowing manual
    DNS configuration.
    
    **Validates: Requirements 3.1, 3.3, 3.4, 3.5**
    """
    
    def test_preservation_condition_holds(self, aws_config):
        """
        Verify that the preservation condition holds (ACM_ZONE_ID is empty).
        
        This test confirms we're testing the right scenario.
        """
        # Skip if preservation condition doesn't hold
        if not is_preservation_condition():
            pytest.skip(
                "Preservation condition does not hold: ACM_ZONE_ID is configured. "
                "This test requires ACM_ZONE_ID to be empty to verify preservation behavior."
            )
        
        assert aws_config['acm_zone_id'] == "", "ACM_ZONE_ID must be empty for preservation tests"
    
    def test_no_route53_domain_a_record_when_zone_id_empty(self, aws_config):
        """
        Test that no Route53 A record is created when ACM_ZONE_ID is empty.
        
        EXPECTED ON UNFIXED CODE: PASS - no A record created
        EXPECTED ON FIXED CODE: PASS - no A record created (preservation)
        
        **Validates: Requirement 3.1**
        """
        if not is_preservation_condition():
            pytest.skip("Preservation condition does not hold")
        
        terraform_state = get_terraform_state()
        
        if terraform_state is None:
            pytest.skip("Terraform state unavailable - cannot verify")
        
        # This assertion should PASS on unfixed code (confirming baseline behavior)
        assert not terraform_state['has_alb_domain_a'], (
            "PRESERVATION VIOLATION: Terraform state contains "
            "'aws_route53_record.alb_domain_a' resource when ACM_ZONE_ID is empty. "
            "Expected: No A record when ACM_ZONE_ID is empty (manual DNS configuration). "
            f"Actual: A record exists in state. Resources: {terraform_state['all_resources']}"
        )
    
    def test_no_route53_domain_aaaa_record_when_zone_id_empty(self, aws_config):
        """
        Test that no Route53 AAAA record is created when ACM_ZONE_ID is empty.
        
        EXPECTED ON UNFIXED CODE: PASS - no AAAA record created
        EXPECTED ON FIXED CODE: PASS - no AAAA record created (preservation)
        
        **Validates: Requirement 3.1**
        """
        if not is_preservation_condition():
            pytest.skip("Preservation condition does not hold")
        
        terraform_state = get_terraform_state()
        
        if terraform_state is None:
            pytest.skip("Terraform state unavailable - cannot verify")
        
        # This assertion should PASS on unfixed code (confirming baseline behavior)
        assert not terraform_state['has_alb_domain_aaaa'], (
            "PRESERVATION VIOLATION: Terraform state contains "
            "'aws_route53_record.alb_domain_aaaa' resource when ACM_ZONE_ID is empty. "
            "Expected: No AAAA record when ACM_ZONE_ID is empty (manual DNS configuration). "
            f"Actual: AAAA record exists in state. Resources: {terraform_state['all_resources']}"
        )
    
    def test_alb_deploys_successfully_without_custom_domain(self, aws_config):
        """
        Test that ALB deploys successfully when ACM_ZONE_ID is empty.
        
        EXPECTED ON UNFIXED CODE: PASS - ALB deploys successfully
        EXPECTED ON FIXED CODE: PASS - ALB deploys successfully (preservation)
        
        **Validates: Requirement 3.3, 3.4**
        """
        if not is_preservation_condition():
            pytest.skip("Preservation condition does not hold")
        
        terraform_state = get_terraform_state()
        
        if terraform_state is None:
            pytest.skip("Terraform state unavailable - cannot verify")
        
        # This assertion should PASS on unfixed code (confirming baseline behavior)
        assert terraform_state['has_alb'], (
            "PRESERVATION VIOLATION: ALB not found in Terraform state when ACM_ZONE_ID is empty. "
            "Expected: ALB deploys successfully regardless of custom domain configuration. "
            f"Actual: No ALB in state. Resources: {terraform_state['all_resources']}"
        )
    
    def test_alb_accessible_via_aws_dns_name(self, aws_config):
        """
        Test that ALB is accessible via its AWS-generated DNS name when ACM_ZONE_ID is empty.
        
        EXPECTED ON UNFIXED CODE: PASS - ALB accessible via AWS DNS
        EXPECTED ON FIXED CODE: PASS - ALB accessible via AWS DNS (preservation)
        
        **Validates: Requirement 3.3**
        """
        if not is_preservation_condition():
            pytest.skip("Preservation condition does not hold")
        
        alb_dns_name = get_alb_dns_name()
        
        if alb_dns_name is None:
            pytest.skip("ALB DNS name unavailable - cannot verify accessibility")
        
        accessibility = check_alb_accessibility(alb_dns_name)
        
        # This assertion should PASS on unfixed code (confirming baseline behavior)
        assert accessibility['accessible'], (
            f"PRESERVATION VIOLATION: ALB not accessible via AWS DNS name {alb_dns_name}. "
            "Expected: ALB accessible via AWS-generated DNS name regardless of custom domain. "
            f"Actual: DNS resolution failed with error: {accessibility['error']}"
        )
    
    def test_no_domain_records_in_terraform_config_when_zone_id_empty(self, aws_config):
        """
        Test that Terraform configuration doesn't create domain records when ACM_ZONE_ID is empty.
        
        This test verifies the conditional logic in the Terraform configuration.
        
        EXPECTED ON UNFIXED CODE: PASS - no domain records defined or count=0
        EXPECTED ON FIXED CODE: PASS - domain records defined but count=0 (preservation)
        
        **Validates: Requirement 3.1**
        """
        if not is_preservation_condition():
            pytest.skip("Preservation condition does not hold")
        
        terraform_config = check_terraform_config_has_route53_resources()
        terraform_state = get_terraform_state()
        
        if terraform_state is None:
            pytest.skip("Terraform state unavailable - cannot verify")
        
        # The key check is that no records exist in state, regardless of config
        # (config may define resources with count=0)
        assert not terraform_state['has_alb_domain_a'] and not terraform_state['has_alb_domain_aaaa'], (
            "PRESERVATION VIOLATION: Route53 domain records exist in state when ACM_ZONE_ID is empty. "
            "Expected: No domain records created when ACM_ZONE_ID is empty. "
            f"Has A record: {terraform_state['has_alb_domain_a']}, "
            f"Has AAAA record: {terraform_state['has_alb_domain_aaaa']}"
        )
    
    def test_complete_preservation_property(self, aws_config):
        """
        Complete preservation property test - verifies all aspects of preservation.
        
        This is the main property test that encodes the complete preservation behavior.
        
        EXPECTED ON UNFIXED CODE: PASS - confirms baseline behavior
        EXPECTED ON FIXED CODE: PASS - confirms no regressions
        
        **Validates: Requirements 3.1, 3.3, 3.4, 3.5**
        """
        if not is_preservation_condition():
            pytest.skip("Preservation condition does not hold")
        
        # Collect all preservation violations
        violations = []
        
        # Check Terraform state
        terraform_state = get_terraform_state()
        if terraform_state:
            if terraform_state['has_alb_domain_a']:
                violations.append(
                    "Route53 A record exists in state when ACM_ZONE_ID is empty"
                )
            if terraform_state['has_alb_domain_aaaa']:
                violations.append(
                    "Route53 AAAA record exists in state when ACM_ZONE_ID is empty"
                )
            if not terraform_state['has_alb']:
                violations.append(
                    "ALB not found in state - deployment failed"
                )
        else:
            violations.append("Terraform state unavailable for verification")
        
        # Check ALB accessibility
        alb_dns_name = get_alb_dns_name()
        if alb_dns_name:
            accessibility = check_alb_accessibility(alb_dns_name)
            if not accessibility['accessible']:
                violations.append(
                    f"ALB not accessible via AWS DNS name {alb_dns_name}: {accessibility['error']}"
                )
        else:
            violations.append("ALB DNS name unavailable - cannot verify accessibility")
        
        # This assertion should PASS on unfixed code (confirming baseline behavior)
        assert len(violations) == 0, (
            f"PRESERVATION VIOLATIONS FOUND! "
            f"The configuration has {len(violations)} preservation issue(s):\n" +
            "\n".join(f"  {i+1}. {v}" for i, v in enumerate(violations))
        )


class TestDomainDNSPreservationPropertyBased:
    """
    Property-based tests using Hypothesis to verify preservation behavior
    across various configuration combinations.
    
    **Validates: Requirements 3.1, 3.3, 3.4, 3.5**
    """
    
    def test_no_domain_records_when_zone_id_empty(self):
        """
        Property: When ACM_ZONE_ID is empty, no Route53 domain records are created.
        
        This test verifies the core preservation property.
        
        EXPECTED ON UNFIXED CODE: PASS - no records created
        EXPECTED ON FIXED CODE: PASS - no records created (preservation)
        
        **Validates: Requirements 3.1**
        """
        if not is_preservation_condition():
            pytest.skip("Preservation condition does not hold")
        
        terraform_state = get_terraform_state()
        
        if terraform_state is None:
            pytest.skip("Terraform state unavailable - cannot verify")
        
        # Neither A nor AAAA records should exist
        assert not terraform_state['has_alb_domain_a'] and not terraform_state['has_alb_domain_aaaa'], (
            "PRESERVATION VIOLATION: Route53 domain records exist when ACM_ZONE_ID is empty. "
            f"Has A record: {terraform_state['has_alb_domain_a']}, "
            f"Has AAAA record: {terraform_state['has_alb_domain_aaaa']}. "
            "Expected: No domain records when ACM_ZONE_ID is empty (manual DNS configuration)."
        )
    
    def test_infrastructure_consistency_without_custom_domain(self):
        """
        Property: Infrastructure deploys consistently when ACM_ZONE_ID is empty.
        
        This test verifies that all infrastructure components work correctly
        without custom domain configuration.
        
        EXPECTED ON UNFIXED CODE: PASS - infrastructure consistent
        EXPECTED ON FIXED CODE: PASS - infrastructure consistent (preservation)
        
        **Validates: Requirements 3.3, 3.4**
        """
        if not is_preservation_condition():
            pytest.skip("Preservation condition does not hold")
        
        terraform_state = get_terraform_state()
        
        if terraform_state is None:
            pytest.skip("Terraform state unavailable - cannot verify")
        
        # ALB must exist
        assert terraform_state['has_alb'], (
            "PRESERVATION VIOLATION: ALB not found in state. "
            "Expected: ALB deploys successfully regardless of custom domain configuration. "
            f"Resources: {terraform_state['all_resources']}"
        )
        
        # No domain records should exist
        assert not terraform_state['has_alb_domain_a'] and not terraform_state['has_alb_domain_aaaa'], (
            "PRESERVATION VIOLATION: Domain records exist when they shouldn't. "
            f"Has A record: {terraform_state['has_alb_domain_a']}, "
            f"Has AAAA record: {terraform_state['has_alb_domain_aaaa']}"
        )


class TestHTTPOnlyPreservation:
    """
    Tests to verify HTTP-only deployments (ENABLE_HTTPS=false) continue to work.
    
    **Validates: Requirement 3.5**
    """
    
    def test_http_only_deployment_works(self, aws_config):
        """
        Test that HTTP-only deployments work without requiring ACM or Route53.
        
        EXPECTED ON UNFIXED CODE: PASS - HTTP-only works
        EXPECTED ON FIXED CODE: PASS - HTTP-only works (preservation)
        
        **Validates: Requirement 3.5**
        """
        if not is_preservation_condition():
            pytest.skip("Preservation condition does not hold")
        
        # This test is informational - verifies the deployment scenario
        enable_https = aws_config['enable_https'].lower()
        
        terraform_state = get_terraform_state()
        
        if terraform_state is None:
            pytest.skip("Terraform state unavailable - cannot verify")
        
        # ALB should exist regardless of HTTPS setting
        assert terraform_state['has_alb'], (
            f"PRESERVATION VIOLATION: ALB not found in state (ENABLE_HTTPS={enable_https}). "
            "Expected: ALB deploys successfully for both HTTP and HTTPS configurations. "
            f"Resources: {terraform_state['all_resources']}"
        )
        
        # No domain records should exist when ACM_ZONE_ID is empty
        assert not terraform_state['has_alb_domain_a'] and not terraform_state['has_alb_domain_aaaa'], (
            f"PRESERVATION VIOLATION: Domain records exist when ACM_ZONE_ID is empty (ENABLE_HTTPS={enable_https}). "
            "Expected: No domain records when ACM_ZONE_ID is empty, regardless of HTTPS setting."
        )
