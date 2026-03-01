# Bugfix Requirements Document

## Introduction

The deployment validation script (`scripts/validate_deployment.sh`) fails when validating deployments that use HTTPS with ACM certificates configured for custom domains. The script attempts to access the ALB via its AWS-generated DNS name (e.g., `https://seva-arogya-dev-alb-1776006542.ap-south-1.elb.amazonaws.com/health`), but the ACM certificate is issued for the custom domain (`sevaarogya.shoppertrends.in`), causing SSL certificate verification to fail with "SSL: no alternative certificate subject name matches target host name".

This causes deployment validation to report failure even when the application is healthy and functioning correctly, leading to false negatives in the deployment pipeline.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the validation script checks an HTTPS endpoint using the ALB DNS name AND the ACM certificate is configured for a custom domain THEN the system fails with SSL certificate verification error

1.2 WHEN curl encounters SSL certificate hostname mismatch THEN the system reports deployment validation failure even though the application is healthy

1.3 WHEN the deployment uses HTTPS with a custom domain certificate THEN the system cannot successfully validate the deployment via the ALB DNS name

### Expected Behavior (Correct)

2.1 WHEN the validation script checks an HTTPS endpoint using the ALB DNS name AND the ACM certificate is configured for a custom domain THEN the system SHALL skip SSL certificate verification for the ALB DNS name

2.2 WHEN curl encounters SSL certificate hostname mismatch for ALB DNS endpoints THEN the system SHALL use the `-k` or `--insecure` flag to bypass certificate verification and successfully validate the health endpoint

2.3 WHEN the deployment uses HTTPS with a custom domain certificate THEN the system SHALL successfully validate deployment health via the ALB DNS name without SSL verification errors

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the validation script checks an HTTP endpoint (non-HTTPS) THEN the system SHALL CONTINUE TO perform validation without any SSL-related flags

3.2 WHEN the validation script successfully receives a 200 response from the health endpoint THEN the system SHALL CONTINUE TO report deployment validation success

3.3 WHEN the validation script receives non-200 responses or connection failures THEN the system SHALL CONTINUE TO retry with the configured retry logic

3.4 WHEN the validation script completes all health checks successfully THEN the system SHALL CONTINUE TO print the success message and detailed AWS connectivity breakdown

3.5 WHEN the validation script is called with an API_BASE_URL parameter THEN the system SHALL CONTINUE TO use that URL for all health check requests
