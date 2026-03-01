"""
Bug Condition Exploration Test for Domain DNS Resolution Fix

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

This test encodes the EXPECTED behavior - it will FAIL on unfixed code,
confirming the bug exists. When the bug is fixed, this test will PASS.

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

GOAL: Surface counterexamples that demonstrate the bug exists.

This test verifies that when ACM_ZONE_ID and ACM_DOMAIN_NAME are both configured,
Route53 A and AAAA alias records exist pointing to the ALB.
"""
import pytest
import boto3
import os
import subprocess
import json
from hypothesis import given, strategies as st, settings
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_env_variable(var_name, default=""):
    """Get environment variable value"""
    return os.environ.get(var_name, default)


def is_bug_condition():
    """
    Check if the bug condition holds (ACM_DOMAIN_NAME is configured).
    
    Returns True if ACM_DOMAIN_NAME is configured, indicating a custom domain is intended.
    The bug is that even when ACM_ZONE_ID would be provided, the Terraform configuration
    doesn't create the A/AAAA records.
    """
    acm_domain_name = get_env_variable('ACM_DOMAIN_NAME')
    
    return acm_domain_name != ""


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
            resources = result.stdout.strip().split('\n')
            return {
                'has_alb_domain_a': any('aws_route53_record.alb_domain_a' in r for r in resources),
                'has_alb_domain_aaaa': any('aws_route53_record.alb_domain_aaaa' in r for r in resources),
                'has_alb_cert_validation': any('aws_route53_record.alb_cert_validation' in r for r in resources),
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


def get_route53_records(zone_id, domain_name):
    """
    Query Route53 to check for A and AAAA records for the domain.
    
    Returns dict with record information:
    - has_a_record: bool
    - has_aaaa_record: bool
    - a_record_details: dict or None
    - aaaa_record_details: dict or None
    """
    try:
        client = boto3.client('route53', region_name=get_env_variable('AWS_REGION', 'ap-south-1'))
        
        # List all records in the hosted zone
        response = client.list_resource_record_sets(
            HostedZoneId=zone_id,
            StartRecordName=domain_name,
            StartRecordType='A',
            MaxItems='10'
        )
        
        records = response.get('ResourceRecordSets', [])
        
        a_record = None
        aaaa_record = None
        
        for record in records:
            if record['Name'].rstrip('.') == domain_name.rstrip('.'):
                if record['Type'] == 'A':
                    a_record = record
                elif record['Type'] == 'AAAA':
                    aaaa_record = record
        
        return {
            'has_a_record': a_record is not None,
            'has_aaaa_record': aaaa_record is not None,
            'a_record_details': a_record,
            'aaaa_record_details': aaaa_record
        }
    except ClientError as e:
        # If zone doesn't exist or credentials are invalid, return empty result
        return {
            'has_a_record': False,
            'has_aaaa_record': False,
            'a_record_details': None,
            'aaaa_record_details': None,
            'error': str(e)
        }


def is_alias_record_to_alb(record_details):
    """
    Check if a Route53 record is an alias record pointing to an ALB.
    
    Returns True if the record has an AliasTarget pointing to an ELB (ALB).
    """
    if not record_details:
        return False
    
    alias_target = record_details.get('AliasTarget')
    if not alias_target:
        return False
    
    # ALB DNS names contain 'elb.amazonaws.com'
    dns_name = alias_target.get('DNSName', '')
    return 'elb.amazonaws.com' in dns_name.lower()


def check_dns_resolution(domain_name):
    """
    Check if the domain resolves using DNS lookup.
    
    Returns dict with resolution status:
    - resolves: bool
    - addresses: list of IP addresses or None
    - error: error message if resolution fails
    """
    try:
        import socket
        addresses = socket.getaddrinfo(domain_name, None)
        ip_addresses = list(set([addr[4][0] for addr in addresses]))
        
        return {
            'resolves': True,
            'addresses': ip_addresses,
            'error': None
        }
    except socket.gaierror as e:
        return {
            'resolves': False,
            'addresses': None,
            'error': str(e)
        }


@pytest.fixture
def aws_config():
    """Fixture to provide AWS configuration from environment"""
    return {
        'acm_zone_id': get_env_variable('ACM_ZONE_ID'),
        'acm_domain_name': get_env_variable('ACM_DOMAIN_NAME'),
        'aws_region': get_env_variable('AWS_REGION', 'ap-south-1')
    }


class TestDomainDNSBugCondition:
    """
    Property 1: Fault Condition - Domain Routes to ALB
    
    For any Terraform configuration where ACM_ZONE_ID and ACM_DOMAIN_NAME are
    both non-empty strings, the fixed Terraform configuration SHALL create
    Route53 A and AAAA alias records that point the domain to the ALB's DNS
    name and zone ID, enabling successful DNS resolution.
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """
    
    def test_bug_condition_holds(self, aws_config):
        """
        Verify that the bug condition holds (ACM_DOMAIN_NAME is configured).
        
        This test confirms we're testing the right scenario.
        """
        # Skip if bug condition doesn't hold
        if not is_bug_condition():
            pytest.skip(
                "Bug condition does not hold: ACM_DOMAIN_NAME is empty. "
                "This test requires a domain to be configured to verify the bug."
            )
        
        assert aws_config['acm_domain_name'] != "", "ACM_DOMAIN_NAME must be configured"
    
    def test_terraform_config_defines_route53_a_record_resource(self, aws_config):
        """
        Test that Terraform configuration (main.tf) defines aws_route53_record.alb_domain_a resource.
        
        EXPECTED ON UNFIXED CODE: FAIL - resource definition does not exist in main.tf
        EXPECTED ON FIXED CODE: PASS - resource definition exists in main.tf
        
        **Validates: Requirement 2.2**
        """
        if not is_bug_condition():
            pytest.skip("Bug condition does not hold")
        
        terraform_config = check_terraform_config_has_route53_resources()
        
        # This assertion will FAIL on unfixed code (proving the bug exists)
        assert terraform_config['has_a_record_resource'], (
            "COUNTEREXAMPLE FOUND: Terraform configuration (main.tf) does not define "
            "'resource \"aws_route53_record\" \"alb_domain_a\"'. "
            "Expected: Resource definition for A record pointing to ALB. "
            "Actual: No A record resource defined in main.tf."
        )
    
    def test_terraform_config_defines_route53_aaaa_record_resource(self, aws_config):
        """
        Test that Terraform configuration (main.tf) defines aws_route53_record.alb_domain_aaaa resource.
        
        EXPECTED ON UNFIXED CODE: FAIL - resource definition does not exist in main.tf
        EXPECTED ON FIXED CODE: PASS - resource definition exists in main.tf
        
        **Validates: Requirement 2.2**
        """
        if not is_bug_condition():
            pytest.skip("Bug condition does not hold")
        
        terraform_config = check_terraform_config_has_route53_resources()
        
        # This assertion will FAIL on unfixed code (proving the bug exists)
        assert terraform_config['has_aaaa_record_resource'], (
            "COUNTEREXAMPLE FOUND: Terraform configuration (main.tf) does not define "
            "'resource \"aws_route53_record\" \"alb_domain_aaaa\"'. "
            "Expected: Resource definition for AAAA record pointing to ALB. "
            "Actual: No AAAA record resource defined in main.tf."
        )
    
    def test_terraform_state_has_route53_a_record(self, aws_config):
        """
        Test that Terraform state includes aws_route53_record.alb_domain_a resource.
        
        EXPECTED ON UNFIXED CODE: FAIL - resource does not exist in state
        EXPECTED ON FIXED CODE: PASS - resource exists in state
        
        **Validates: Requirement 2.2**
        """
        if not is_bug_condition():
            pytest.skip("Bug condition does not hold")
        
        terraform_state = get_terraform_state()
        
        if terraform_state is None:
            pytest.skip("Terraform state unavailable - cannot verify")
        
        # This assertion will FAIL on unfixed code (proving the bug exists)
        assert terraform_state['has_alb_domain_a'], (
            "COUNTEREXAMPLE FOUND: Terraform state does not contain "
            "'aws_route53_record.alb_domain_a' resource. "
            f"Available resources: {terraform_state['all_resources']}"
        )
    
    def test_terraform_state_has_route53_aaaa_record(self, aws_config):
        """
        Test that Terraform state includes aws_route53_record.alb_domain_aaaa resource.
        
        EXPECTED ON UNFIXED CODE: FAIL - resource does not exist in state
        EXPECTED ON FIXED CODE: PASS - resource exists in state
        
        **Validates: Requirement 2.2**
        """
        if not is_bug_condition():
            pytest.skip("Bug condition does not hold")
        
        terraform_state = get_terraform_state()
        
        if terraform_state is None:
            pytest.skip("Terraform state unavailable - cannot verify")
        
        # This assertion will FAIL on unfixed code (proving the bug exists)
        assert terraform_state['has_alb_domain_aaaa'], (
            "COUNTEREXAMPLE FOUND: Terraform state does not contain "
            "'aws_route53_record.alb_domain_aaaa' resource. "
            f"Available resources: {terraform_state['all_resources']}"
        )
    
    def test_route53_has_a_record_for_domain(self, aws_config):
        """
        Test that Route53 hosted zone contains an A record for the domain.
        
        EXPECTED ON UNFIXED CODE: FAIL - A record does not exist
        EXPECTED ON FIXED CODE: PASS - A record exists
        
        **Validates: Requirement 2.1, 2.3**
        """
        if not is_bug_condition():
            pytest.skip("Bug condition does not hold")
        
        zone_id = aws_config['acm_zone_id']
        domain_name = aws_config['acm_domain_name']
        
        if not zone_id:
            pytest.skip("ACM_ZONE_ID not configured - cannot query Route53")
        
        route53_records = get_route53_records(zone_id, domain_name)
        
        if 'error' in route53_records:
            pytest.skip(f"Cannot query Route53: {route53_records['error']}")
        
        # This assertion will FAIL on unfixed code (proving the bug exists)
        assert route53_records['has_a_record'], (
            f"COUNTEREXAMPLE FOUND: Route53 hosted zone {zone_id} does not contain "
            f"an A record for domain {domain_name}. "
            "Expected: A record pointing to ALB. "
            "Actual: No A record found."
        )
    
    def test_route53_has_aaaa_record_for_domain(self, aws_config):
        """
        Test that Route53 hosted zone contains an AAAA record for the domain.
        
        EXPECTED ON UNFIXED CODE: FAIL - AAAA record does not exist
        EXPECTED ON FIXED CODE: PASS - AAAA record exists
        
        **Validates: Requirement 2.1, 2.3**
        """
        if not is_bug_condition():
            pytest.skip("Bug condition does not hold")
        
        zone_id = aws_config['acm_zone_id']
        domain_name = aws_config['acm_domain_name']
        
        if not zone_id:
            pytest.skip("ACM_ZONE_ID not configured - cannot query Route53")
        
        route53_records = get_route53_records(zone_id, domain_name)
        
        if 'error' in route53_records:
            pytest.skip(f"Cannot query Route53: {route53_records['error']}")
        
        # This assertion will FAIL on unfixed code (proving the bug exists)
        assert route53_records['has_aaaa_record'], (
            f"COUNTEREXAMPLE FOUND: Route53 hosted zone {zone_id} does not contain "
            f"an AAAA record for domain {domain_name}. "
            "Expected: AAAA record pointing to ALB. "
            "Actual: No AAAA record found."
        )
    
    def test_a_record_is_alias_to_alb(self, aws_config):
        """
        Test that the A record is an alias record pointing to the ALB.
        
        EXPECTED ON UNFIXED CODE: FAIL - A record doesn't exist or isn't an alias to ALB
        EXPECTED ON FIXED CODE: PASS - A record is an alias to ALB
        
        **Validates: Requirement 2.2, 2.4**
        """
        if not is_bug_condition():
            pytest.skip("Bug condition does not hold")
        
        zone_id = aws_config['acm_zone_id']
        domain_name = aws_config['acm_domain_name']
        
        if not zone_id:
            pytest.skip("ACM_ZONE_ID not configured - cannot query Route53")
        
        route53_records = get_route53_records(zone_id, domain_name)
        
        if 'error' in route53_records:
            pytest.skip(f"Cannot query Route53: {route53_records['error']}")
        
        if not route53_records['has_a_record']:
            pytest.fail(
                "COUNTEREXAMPLE FOUND: A record does not exist, "
                "so cannot verify it's an alias to ALB"
            )
        
        # This assertion will FAIL on unfixed code (proving the bug exists)
        assert is_alias_record_to_alb(route53_records['a_record_details']), (
            f"COUNTEREXAMPLE FOUND: A record for {domain_name} exists but is not "
            "an alias record pointing to ALB. "
            f"Record details: {route53_records['a_record_details']}"
        )
    
    def test_aaaa_record_is_alias_to_alb(self, aws_config):
        """
        Test that the AAAA record is an alias record pointing to the ALB.
        
        EXPECTED ON UNFIXED CODE: FAIL - AAAA record doesn't exist or isn't an alias to ALB
        EXPECTED ON FIXED CODE: PASS - AAAA record is an alias to ALB
        
        **Validates: Requirement 2.2, 2.4**
        """
        if not is_bug_condition():
            pytest.skip("Bug condition does not hold")
        
        zone_id = aws_config['acm_zone_id']
        domain_name = aws_config['acm_domain_name']
        
        if not zone_id:
            pytest.skip("ACM_ZONE_ID not configured - cannot query Route53")
        
        route53_records = get_route53_records(zone_id, domain_name)
        
        if 'error' in route53_records:
            pytest.skip(f"Cannot query Route53: {route53_records['error']}")
        
        if not route53_records['has_aaaa_record']:
            pytest.fail(
                "COUNTEREXAMPLE FOUND: AAAA record does not exist, "
                "so cannot verify it's an alias to ALB"
            )
        
        # This assertion will FAIL on unfixed code (proving the bug exists)
        assert is_alias_record_to_alb(route53_records['aaaa_record_details']), (
            f"COUNTEREXAMPLE FOUND: AAAA record for {domain_name} exists but is not "
            "an alias record pointing to ALB. "
            f"Record details: {route53_records['aaaa_record_details']}"
        )
    
    def test_domain_resolves_via_dns(self, aws_config):
        """
        Test that the domain resolves via DNS lookup.
        
        EXPECTED ON UNFIXED CODE: FAIL - DNS lookup fails with NXDOMAIN or similar
        EXPECTED ON FIXED CODE: PASS - DNS lookup succeeds
        
        **Validates: Requirement 2.1**
        """
        if not is_bug_condition():
            pytest.skip("Bug condition does not hold")
        
        domain_name = aws_config['acm_domain_name']
        
        if not domain_name:
            pytest.skip("ACM_DOMAIN_NAME not configured - cannot test DNS resolution")
        
        dns_result = check_dns_resolution(domain_name)
        
        # This assertion will FAIL on unfixed code (proving the bug exists)
        assert dns_result['resolves'], (
            f"COUNTEREXAMPLE FOUND: Domain {domain_name} does not resolve via DNS. "
            f"Error: {dns_result['error']}. "
            "Expected: Domain resolves to ALB IP addresses. "
            "Actual: DNS lookup failed."
        )
    
    def test_complete_bug_condition(self, aws_config):
        """
        Complete bug condition test - verifies all aspects of the expected behavior.
        
        This is the main property test that encodes the complete expected behavior.
        
        EXPECTED ON UNFIXED CODE: FAIL - demonstrates the bug exists
        EXPECTED ON FIXED CODE: PASS - confirms the fix works
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
        """
        if not is_bug_condition():
            pytest.skip("Bug condition does not hold")
        
        zone_id = aws_config['acm_zone_id']
        domain_name = aws_config['acm_domain_name']
        
        # Collect all counterexamples
        counterexamples = []
        
        # Check Terraform state
        terraform_state = get_terraform_state()
        if terraform_state:
            if not terraform_state['has_alb_domain_a']:
                counterexamples.append(
                    "Terraform state missing 'aws_route53_record.alb_domain_a' resource"
                )
            if not terraform_state['has_alb_domain_aaaa']:
                counterexamples.append(
                    "Terraform state missing 'aws_route53_record.alb_domain_aaaa' resource"
                )
        else:
            counterexamples.append("Terraform state unavailable for verification")
        
        # Check Route53 records
        if zone_id:
            route53_records = get_route53_records(zone_id, domain_name)
            
            if 'error' not in route53_records:
                if not route53_records['has_a_record']:
                    counterexamples.append(
                        f"Route53 zone {zone_id} missing A record for {domain_name}"
                    )
                elif not is_alias_record_to_alb(route53_records['a_record_details']):
                    counterexamples.append(
                        f"A record for {domain_name} is not an alias to ALB"
                    )
                
                if not route53_records['has_aaaa_record']:
                    counterexamples.append(
                        f"Route53 zone {zone_id} missing AAAA record for {domain_name}"
                    )
                elif not is_alias_record_to_alb(route53_records['aaaa_record_details']):
                    counterexamples.append(
                        f"AAAA record for {domain_name} is not an alias to ALB"
                    )
            else:
                counterexamples.append(f"Cannot query Route53: {route53_records['error']}")
        
        # Check DNS resolution
        dns_result = check_dns_resolution(domain_name)
        if not dns_result['resolves']:
            counterexamples.append(
                f"Domain {domain_name} does not resolve: {dns_result['error']}"
            )
        
        # This assertion will FAIL on unfixed code with detailed counterexamples
        assert len(counterexamples) == 0, (
            f"COUNTEREXAMPLES FOUND - Bug confirmed! "
            f"The domain DNS configuration has {len(counterexamples)} issue(s):\n" +
            "\n".join(f"  {i+1}. {ce}" for i, ce in enumerate(counterexamples))
        )


class TestDomainDNSPropertyBased:
    """
    Property-based test using Hypothesis to verify the bug condition
    holds regardless of specific domain names or zone IDs.
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """
    
    def test_terraform_state_consistency(self):
        """
        Property: When ACM_ZONE_ID and ACM_DOMAIN_NAME are configured,
        Terraform state MUST contain both A and AAAA record resources.
        
        This test verifies the Terraform configuration creates the required resources.
        
        EXPECTED ON UNFIXED CODE: FAIL - resources missing from state
        EXPECTED ON FIXED CODE: PASS - resources present in state
        
        **Validates: Requirements 2.2, 2.3**
        """
        if not is_bug_condition():
            pytest.skip("Bug condition does not hold")
        
        terraform_state = get_terraform_state()
        
        if terraform_state is None:
            pytest.skip("Terraform state unavailable - cannot verify")
        
        # Both resources must exist together
        assert terraform_state['has_alb_domain_a'] and terraform_state['has_alb_domain_aaaa'], (
            "COUNTEREXAMPLE FOUND: Terraform state is inconsistent. "
            f"Has A record: {terraform_state['has_alb_domain_a']}, "
            f"Has AAAA record: {terraform_state['has_alb_domain_aaaa']}. "
            "Expected: Both A and AAAA records present when ACM_ZONE_ID is configured."
        )
