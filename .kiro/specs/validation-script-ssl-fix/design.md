# Bugfix Design Document

## Technical Context

The deployment validation script (`scripts/validate_deployment.sh`) uses curl to perform health checks on the deployed application. When HTTPS is enabled with an ACM certificate configured for a custom domain (e.g., `sevaarogya.shoppertrends.in`), the script accesses the ALB via its AWS DNS name (e.g., `https://seva-arogya-dev-alb-1776006542.ap-south-1.elb.amazonaws.com`). This causes SSL certificate verification to fail because the certificate's Subject Alternative Name (SAN) only includes the custom domain, not the ALB DNS name.

The core issue is in the `check_endpoint()` function at line 41, which uses:
```bash
response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null || echo "000")
```

This curl command performs SSL certificate verification by default, which fails when the hostname doesn't match the certificate.

## Bug Condition

```pascal
FUNCTION isBugCondition(url)
  INPUT: url of type String
  OUTPUT: boolean
  
  // Bug occurs when URL uses HTTPS protocol
  RETURN url starts_with "https://"
END FUNCTION
```

## Fix Specification

```pascal
// Property: Fix Checking - SSL Verification Bypass for HTTPS URLs
FOR ALL url WHERE isBugCondition(url) DO
  result ← check_endpoint_with_insecure_flag(url)
  ASSERT result.success = true OR result.http_code != "SSL_ERROR"
END FOR
```

```pascal
// Property: Preservation Checking - HTTP URLs unchanged
FOR ALL url WHERE NOT isBugCondition(url) DO
  ASSERT check_endpoint_original(url) = check_endpoint_fixed(url)
END FOR
```

## Implementation Approach

Modify the `check_endpoint()` function to detect HTTPS URLs and add the `-k` (insecure) flag to curl when accessing HTTPS endpoints. This bypasses SSL certificate verification for the ALB DNS name while maintaining all other validation logic.

### Changes Required

1. Update the `check_endpoint()` function to detect if the URL uses HTTPS
2. Add the `-k` flag to curl when the URL starts with `https://`
3. Maintain all existing retry logic, response parsing, and error handling

### Code Change

In `scripts/validate_deployment.sh`, modify the curl command in the `check_endpoint()` function:

```bash
# Determine if we need to skip SSL verification for HTTPS URLs
local curl_opts="-s -w \n%{http_code}"
if [[ "$url" == https://* ]]; then
  curl_opts="$curl_opts -k"
fi

response=$(curl $curl_opts "$url" 2>/dev/null || echo "000")
```

## Correctness Properties

### Fix Checking Properties

1. **HTTPS URL Handling**: For all HTTPS URLs, curl SHALL use the `-k` flag to bypass SSL certificate verification
2. **Health Check Success**: For all HTTPS URLs where the application is healthy, the validation SHALL return HTTP 200 without SSL errors
3. **Error Propagation**: For all HTTPS URLs where the application is unhealthy, the validation SHALL still detect and report the actual health check failure

### Preservation Properties

1. **HTTP URL Behavior**: For all HTTP URLs, curl SHALL NOT use the `-k` flag and SHALL behave identically to the original implementation
2. **Retry Logic**: For all URLs (HTTP and HTTPS), the retry logic with max_retries and retry_delay SHALL remain unchanged
3. **Response Parsing**: For all URLs, the response parsing logic (extracting http_code and body) SHALL remain unchanged
4. **Success Criteria**: For all URLs, the success criteria (HTTP 200) SHALL remain unchanged
5. **Error Messages**: For all URLs, the error messages and logging output SHALL remain unchanged

## Testing Strategy

### Fix Validation Tests

1. Test HTTPS URL with certificate mismatch (ALB DNS name with custom domain cert) - should succeed
2. Test HTTPS URL with valid certificate - should succeed
3. Test HTTPS URL with unhealthy application - should fail with appropriate error (not SSL error)

### Preservation Tests

1. Test HTTP URL with healthy application - should succeed (unchanged behavior)
2. Test HTTP URL with unhealthy application - should fail with retry logic (unchanged behavior)
3. Test retry logic with 503 responses - should retry correctly (unchanged behavior)
4. Test response body parsing and AWS connectivity details - should work correctly (unchanged behavior)

## Counterexample

**Before Fix:**
```bash
$ curl -s -w "\n%{http_code}" "https://seva-arogya-dev-alb-1776006542.ap-south-1.elb.amazonaws.com/health"
# Returns: SSL certificate problem: no alternative certificate subject name matches target host name
# Exit code: 60 (SSL verification failure)
```

**After Fix:**
```bash
$ curl -s -k -w "\n%{http_code}" "https://seva-arogya-dev-alb-1776006542.ap-south-1.elb.amazonaws.com/health"
# Returns: {"status":"healthy"}\n200
# Exit code: 0 (success)
```
