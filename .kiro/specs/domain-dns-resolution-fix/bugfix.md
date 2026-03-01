# Bugfix Requirements Document

## Introduction

The domain sevaarogya.shoppertrends.in is not resolving to the Application Load Balancer (ALB), causing DNS lookup failures with ENOTFOUND errors. While the infrastructure successfully deploys an ALB with an ACM certificate, no Route53 DNS records are created to point the domain to the load balancer. This prevents users from accessing the application via the configured domain name.

The root cause is that the Terraform configuration only handles ACM certificate DNS validation records but does not create the A/AAAA alias records needed to route traffic from the domain to the ALB. The ACM_ZONE_ID variable is empty in the .env file, indicating no Route53 hosted zone is configured for DNS management.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user attempts to access http://sevaarogya.shoppertrends.in/ THEN the system fails with DNS lookup error ENOTFOUND

1.2 WHEN Terraform applies the infrastructure configuration THEN the system creates an ALB but does not create Route53 A/AAAA alias records pointing the domain to the ALB

1.3 WHEN ACM_ZONE_ID is empty in the .env file THEN the system only creates ACM certificate validation records but skips creating the domain-to-ALB DNS records

1.4 WHEN the ALB is deployed and accessible via its AWS-generated DNS name THEN the system does not provide any Route53 records to map the custom domain to this ALB endpoint

### Expected Behavior (Correct)

2.1 WHEN a user attempts to access http://sevaarogya.shoppertrends.in/ (or https://) THEN the system SHALL resolve the domain to the ALB's IP address and serve the application

2.2 WHEN Terraform applies the infrastructure configuration with a valid ACM_ZONE_ID THEN the system SHALL create Route53 A and AAAA alias records pointing sevaarogya.shoppertrends.in to the ALB

2.3 WHEN ACM_ZONE_ID is provided in the .env file THEN the system SHALL use this hosted zone to create both ACM validation records and domain-to-ALB routing records

2.4 WHEN the ALB is deployed THEN the system SHALL automatically configure DNS records to make the domain resolve to the load balancer endpoint

### Unchanged Behavior (Regression Prevention)

3.1 WHEN ACM_ZONE_ID is empty or not provided THEN the system SHALL CONTINUE TO deploy the ALB without attempting to create Route53 records (allowing manual DNS configuration)

3.2 WHEN the ACM certificate validation records are created THEN the system SHALL CONTINUE TO use the existing aws_route53_record.alb_cert_validation resource pattern

3.3 WHEN the ALB is deployed without a custom domain THEN the system SHALL CONTINUE TO be accessible via the AWS-generated ALB DNS name

3.4 WHEN other infrastructure components (VPC, ECS, RDS, S3, Cognito) are deployed THEN the system SHALL CONTINUE TO function identically regardless of DNS configuration

3.5 WHEN ENABLE_HTTPS is false THEN the system SHALL CONTINUE TO support HTTP-only access without requiring ACM certificates or Route53 configuration
