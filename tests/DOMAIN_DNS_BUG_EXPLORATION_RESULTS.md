# Domain DNS Resolution Bug Exploration Results

## Test Execution Date
Test executed on unfixed code to confirm bug exists.

## Bug Condition
- **ACM_DOMAIN_NAME**: sevaarogya.shoppertrends.in (configured)
- **ACM_ZONE_ID**: (empty - but bug exists even when this would be configured)

## Counterexamples Found

The bug exploration tests successfully identified the following counterexamples that confirm the bug exists:

### 1. Terraform Configuration Missing Route53 A Record Resource
**Test**: `test_terraform_config_defines_route53_a_record_resource`
**Result**: FAILED (as expected on unfixed code)
**Counterexample**: Terraform configuration (main.tf) does not define `resource "aws_route53_record" "alb_domain_a"`.
- **Expected**: Resource definition for A record pointing to ALB
- **Actual**: No A record resource defined in main.tf

### 2. Terraform Configuration Missing Route53 AAAA Record Resource
**Test**: `test_terraform_config_defines_route53_aaaa_record_resource`
**Result**: FAILED (as expected on unfixed code)
**Counterexample**: Terraform configuration (main.tf) does not define `resource "aws_route53_record" "alb_domain_aaaa"`.
- **Expected**: Resource definition for AAAA record pointing to ALB
- **Actual**: No AAAA record resource defined in main.tf

### 3. Terraform State Missing Route53 A Record
**Test**: `test_terraform_state_has_route53_a_record`
**Result**: FAILED (as expected on unfixed code)
**Counterexample**: Terraform state does not contain `aws_route53_record.alb_domain_a` resource.
- **Available resources**: 64 resources deployed including ALB, ACM certificate, VPC, ECS, RDS, etc.
- **Missing**: aws_route53_record.alb_domain_a

### 4. Terraform State Missing Route53 AAAA Record
**Test**: `test_terraform_state_has_route53_aaaa_record`
**Result**: FAILED (as expected on unfixed code)
**Counterexample**: Terraform state does not contain `aws_route53_record.alb_domain_aaaa` resource.
- **Available resources**: 64 resources deployed including ALB, ACM certificate, VPC, ECS, RDS, etc.
- **Missing**: aws_route53_record.alb_domain_aaaa

### 5. Domain Does Not Resolve via DNS
**Test**: `test_domain_resolves_via_dns`
**Result**: FAILED (as expected on unfixed code)
**Counterexample**: Domain sevaarogya.shoppertrends.in does not resolve via DNS.
- **Error**: [Errno 11001] getaddrinfo failed
- **Expected**: Domain resolves to ALB IP addresses
- **Actual**: DNS lookup failed

### 6. Complete Bug Condition Test
**Test**: `test_complete_bug_condition`
**Result**: FAILED (as expected on unfixed code)
**Counterexamples Found**: 3 issues
1. Terraform state missing 'aws_route53_record.alb_domain_a' resource
2. Terraform state missing 'aws_route53_record.alb_domain_aaaa' resource
3. Domain sevaarogya.shoppertrends.in does not resolve: [Errno 11001] getaddrinfo failed

## Root Cause Confirmation

The counterexamples confirm the hypothesized root cause:

1. **Missing Route53 Resources**: The main.tf file does NOT contain `aws_route53_record.alb_domain_a` or `aws_route53_record.alb_domain_aaaa` resource definitions.

2. **Incomplete DNS Automation**: While the configuration creates an ACM certificate (`aws_acm_certificate.alb[0]` exists in state), it does not create the domain-to-ALB routing records.

3. **Configuration Gap**: The ALB module exposes `alb_dns_name` and `alb_zone_id` outputs, but these are not consumed by any Route53 alias record resources in main.tf.

## Infrastructure State Analysis

Current Terraform state shows:
- ✅ ALB deployed: `module.alb.aws_lb.main`
- ✅ ACM certificate created: `aws_acm_certificate.alb[0]`
- ✅ HTTPS listener configured: `module.alb.aws_lb_listener.https[0]`
- ❌ No Route53 A record for domain
- ❌ No Route53 AAAA record for domain
- ❌ No Route53 validation record (ACM_ZONE_ID is empty)

## Expected Behavior After Fix

When the fix is implemented:
1. Terraform configuration will define `aws_route53_record.alb_domain_a` resource
2. Terraform configuration will define `aws_route53_record.alb_domain_aaaa` resource
3. Both resources will use conditional count based on `var.acm_domain_name != "" && var.acm_zone_id != ""`
4. Both resources will create alias records pointing to ALB DNS name and zone ID
5. Domain will resolve to ALB IP addresses
6. All bug exploration tests will PASS

## Test Status

**Status**: Bug exploration tests PASSED (they correctly failed on unfixed code, confirming the bug exists)

These tests encode the expected behavior and will be used to validate the fix in task 3.3.
