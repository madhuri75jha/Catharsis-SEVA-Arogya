# Tasks

## 1. Implementation Tasks

- [x] 1.1 Modify check_endpoint() function to detect HTTPS URLs and add -k flag to curl
- [x] 1.2 Test the fix with HTTPS URL using ALB DNS name
- [x] 1.3 Verify HTTP URLs still work without -k flag

## 2. Validation Tasks

- [x] 2.1 Run validation script against HTTPS endpoint with certificate mismatch
- [x] 2.2 Run validation script against HTTP endpoint to verify unchanged behavior
- [x] 2.3 Verify retry logic still works correctly for both HTTP and HTTPS
