# Domain DNS Resolution Fix - Bugfix Design

## Overview

The bug prevents users from accessing the application via the custom domain sevaarogya.shoppertrends.in because no Route53 DNS records exist to route traffic from the domain to the Application Load Balancer (ALB). While the Terraform configuration successfully creates ACM certificate validation records, it lacks the critical A and AAAA alias records that map the domain name to the ALB endpoint.

The fix involves adding two new Route53 record resources in the main Terraform configuration that create IPv4 (A) and IPv6 (AAAA) alias records pointing to the ALB. These records will only be created when ACM_ZONE_ID is provided, maintaining backward compatibility for deployments that don't use custom domains.

## Glossary

- **Bug_Condition (C)**: The condition where ACM_ZONE_ID is configured but no A/AAAA alias records exist to route domain traffic to the ALB
- **Property (P)**: When ACM_ZONE_ID is provided, Route53 A and AAAA alias records must exist pointing the domain to the ALB
- **Preservation**: Existing behavior when ACM_ZONE_ID is empty (manual DNS configuration) and ACM validation record creation must remain unchanged
- **ALB (Application Load Balancer)**: The AWS load balancer resource that distributes traffic to ECS tasks
- **Route53 Alias Record**: A special DNS record type that routes traffic to AWS resources like ALBs without exposing IP addresses
- **ACM_ZONE_ID**: The Route53 hosted zone ID variable that controls whether automated DNS record creation is enabled
- **aws_lb.main**: The ALB resource defined in modules/alb/main.tf that exposes dns_name and zone_id outputs

## Bug Details

### Fault Condition

The bug manifests when a user has configured ACM_ZONE_ID in their .env file (indicating they want automated DNS management) but the Terraform configuration only creates ACM validation records without creating the domain-to-ALB routing records. The system successfully deploys infrastructure but leaves the domain unresolvable.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type TerraformConfiguration
  OUTPUT: boolean
  
  RETURN input.acm_zone_id != ""
         AND input.acm_domain_name != ""
         AND existsResource("aws_route53_record.alb_cert_validation")
         AND NOT existsResource("aws_route53_record.alb_domain_a")
         AND NOT existsResource("aws_route53_record.alb_domain_aaaa")
END FUNCTION
```

### Examples

- **Example 1**: User sets ACM_ZONE_ID=Z1234567890ABC and ACM_DOMAIN_NAME=sevaarogya.shoppertrends.in in .env, runs terraform apply. Expected: Domain resolves to ALB. Actual: DNS lookup fails with ENOTFOUND.

- **Example 2**: User deploys infrastructure with ACM_ZONE_ID configured. Expected: Route53 shows A and AAAA records for sevaarogya.shoppertrends.in pointing to ALB. Actual: Only TXT validation record exists.

- **Example 3**: User accesses http://sevaarogya.shoppertrends.in/ after deployment. Expected: Application loads from ALB. Actual: Browser shows "This site can't be reached" DNS error.

- **Edge Case**: User sets ACM_ZONE_ID but leaves ACM_DOMAIN_NAME empty. Expected: No DNS records created (invalid configuration). Actual: Same behavior (no records created).

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Deployments with empty ACM_ZONE_ID must continue to work without attempting Route53 record creation
- ACM certificate validation record creation (aws_route53_record.alb_cert_validation) must continue using the existing pattern
- ALB must remain accessible via its AWS-generated DNS name regardless of custom domain configuration
- All other infrastructure components (VPC, ECS, RDS, S3, Cognito) must function identically
- HTTP-only deployments (ENABLE_HTTPS=false) must continue to work without requiring ACM or Route53

**Scope:**
All Terraform configurations that do NOT have both ACM_ZONE_ID and ACM_DOMAIN_NAME populated should be completely unaffected by this fix. This includes:
- Deployments with empty ACM_ZONE_ID (manual DNS configuration)
- Deployments without custom domains
- Existing ACM validation logic and certificate creation

## Hypothesized Root Cause

Based on the bug description and code analysis, the root cause is:

1. **Missing Route53 Resources**: The main.tf file contains aws_route53_record.alb_cert_validation for ACM validation but lacks corresponding resources for domain-to-ALB routing (A and AAAA alias records).

2. **Incomplete DNS Automation**: The developer implemented ACM certificate automation but did not complete the DNS automation by adding the final routing records that make the domain accessible.

3. **Configuration Gap**: The ACM_ZONE_ID variable exists and is used for validation records, but the same variable is not leveraged to create the domain routing records.

4. **Missing ALB Output References**: While the ALB module exposes alb_dns_name and alb_zone_id outputs, these are not consumed by any Route53 alias record resources in main.tf.

## Correctness Properties

Property 1: Fault Condition - Domain Routes to ALB

_For any_ Terraform configuration where ACM_ZONE_ID and ACM_DOMAIN_NAME are both non-empty strings, the fixed Terraform configuration SHALL create Route53 A and AAAA alias records that point the domain to the ALB's DNS name and zone ID, enabling successful DNS resolution.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 2: Preservation - Manual DNS Configuration Support

_For any_ Terraform configuration where ACM_ZONE_ID is empty or not provided, the fixed Terraform configuration SHALL produce exactly the same infrastructure as the original configuration, creating no Route53 records and allowing manual DNS configuration.

**Validates: Requirements 3.1, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `seva-arogya-infra/main.tf`

**Location**: After the existing aws_route53_record.alb_cert_validation resource (around line 38)

**Specific Changes**:

1. **Add Route53 A Record Resource**: Create aws_route53_record.alb_domain_a resource
   - Use conditional count based on var.acm_domain_name != "" && var.acm_zone_id != ""
   - Set zone_id to var.acm_zone_id
   - Set name to var.acm_domain_name
   - Set type to "A"
   - Configure alias block pointing to module.alb.alb_dns_name and module.alb.alb_zone_id
   - Set evaluate_target_health to true for health checking

2. **Add Route53 AAAA Record Resource**: Create aws_route53_record.alb_domain_aaaa resource
   - Use identical conditional count as A record
   - Set zone_id to var.acm_zone_id
   - Set name to var.acm_domain_name
   - Set type to "AAAA"
   - Configure alias block with same ALB references
   - Set evaluate_target_health to true

3. **Maintain Conditional Logic**: Ensure both resources use the same condition as ACM validation records to maintain consistency

4. **Use ALB Module Outputs**: Reference module.alb.alb_dns_name and module.alb.alb_zone_id which are already exposed by the ALB module

5. **Add Dependency Management**: Ensure records are created after ALB module is ready (implicit through module output references)

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code by verifying DNS records are missing, then verify the fix creates the correct records and preserves existing behavior for configurations without custom domains.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that when ACM_ZONE_ID is configured, no A/AAAA records are created.

**Test Plan**: Deploy the UNFIXED Terraform configuration with ACM_ZONE_ID and ACM_DOMAIN_NAME set, then query Route53 to verify that only validation records exist and no A/AAAA alias records are present. This confirms the root cause.

**Test Cases**:
1. **Missing A Record Test**: Deploy with ACM_ZONE_ID set, query Route53 for A record (will fail - record not found on unfixed code)
2. **Missing AAAA Record Test**: Deploy with ACM_ZONE_ID set, query Route53 for AAAA record (will fail - record not found on unfixed code)
3. **DNS Resolution Test**: Attempt to resolve sevaarogya.shoppertrends.in using dig or nslookup (will fail with NXDOMAIN on unfixed code)
4. **Terraform State Inspection**: Run terraform state list and verify aws_route53_record.alb_domain_a and aws_route53_record.alb_domain_aaaa do not exist (will confirm missing resources on unfixed code)

**Expected Counterexamples**:
- Route53 hosted zone contains only TXT validation record, no A or AAAA records
- DNS queries for the domain return NXDOMAIN or SERVFAIL
- Terraform state shows aws_route53_record.alb_cert_validation but not domain routing records
- Possible causes: missing resource definitions, incorrect conditional logic, missing ALB output references

### Fix Checking

**Goal**: Verify that for all Terraform configurations where the bug condition holds (ACM_ZONE_ID and ACM_DOMAIN_NAME are set), the fixed configuration creates the required DNS records.

**Pseudocode:**
```
FOR ALL config WHERE isBugCondition(config) DO
  result := terraform_apply_fixed(config)
  ASSERT existsRoute53Record(config.acm_domain_name, "A", config.acm_zone_id)
  ASSERT existsRoute53Record(config.acm_domain_name, "AAAA", config.acm_zone_id)
  ASSERT route53RecordPointsToALB(config.acm_domain_name, module.alb.alb_dns_name)
  ASSERT dnsResolves(config.acm_domain_name)
END FOR
```

### Preservation Checking

**Goal**: Verify that for all Terraform configurations where the bug condition does NOT hold (ACM_ZONE_ID is empty), the fixed configuration produces identical infrastructure to the original.

**Pseudocode:**
```
FOR ALL config WHERE NOT isBugCondition(config) DO
  original_state := terraform_apply_original(config)
  fixed_state := terraform_apply_fixed(config)
  ASSERT original_state.resources = fixed_state.resources
  ASSERT NOT existsRoute53Record(*, *, *)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many Terraform variable combinations automatically
- It catches edge cases like partial configuration (only ACM_ZONE_ID set, only ACM_DOMAIN_NAME set)
- It provides strong guarantees that behavior is unchanged for all non-buggy configurations

**Test Plan**: Deploy UNFIXED code with various configurations (empty ACM_ZONE_ID, empty ACM_DOMAIN_NAME, both empty), observe that ALB deploys successfully and is accessible via AWS DNS name, then verify FIXED code produces identical results.

**Test Cases**:
1. **Empty ACM_ZONE_ID Preservation**: Deploy with ACM_ZONE_ID="" and verify no Route53 records are created (should match unfixed behavior)
2. **Empty ACM_DOMAIN_NAME Preservation**: Deploy with ACM_DOMAIN_NAME="" and verify no Route53 records are created (should match unfixed behavior)
3. **Both Empty Preservation**: Deploy with both variables empty and verify ALB is accessible via AWS DNS name (should match unfixed behavior)
4. **HTTP-Only Preservation**: Deploy with ENABLE_HTTPS=false and verify infrastructure works identically (should match unfixed behavior)

### Unit Tests

- Test Terraform plan output with ACM_ZONE_ID set shows aws_route53_record.alb_domain_a and aws_route53_record.alb_domain_aaaa resources
- Test Terraform plan output with ACM_ZONE_ID empty shows zero Route53 domain records
- Test that A record alias block references correct ALB DNS name and zone ID
- Test that AAAA record alias block references correct ALB DNS name and zone ID
- Test conditional count logic evaluates correctly for various variable combinations

### Property-Based Tests

- Generate random combinations of ACM_ZONE_ID (empty/non-empty) and ACM_DOMAIN_NAME (empty/non-empty) and verify correct record creation behavior
- Generate random domain names and verify Route53 records use the correct name value
- Generate random zone IDs and verify Route53 records target the correct hosted zone
- Test that all configurations without custom domains continue to deploy successfully

### Integration Tests

- Deploy full infrastructure with ACM_ZONE_ID set and verify domain resolves to ALB IP addresses
- Access application via custom domain (http://sevaarogya.shoppertrends.in/) and verify it loads correctly
- Verify ACM certificate validation continues to work alongside domain routing records
- Test that ALB health checks pass and ECS tasks receive traffic through custom domain
- Verify DNS propagation by querying Route53 nameservers directly
