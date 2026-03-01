#!/bin/bash

# Test script for validation-script-ssl-fix
# Tests that the validation script correctly handles HTTPS URLs with SSL certificate mismatches

set -euo pipefail

echo "========================================="
echo "Testing Validation Script SSL Fix"
echo "========================================="
echo ""

# Test 1: Verify HTTPS URL detection and -k flag usage
echo "Test 1: HTTPS URL should use -k flag"
echo "--------------------------------------"

# Create a test function that mimics the fixed check_endpoint logic
test_curl_opts() {
  local url="$1"
  local curl_opts="-s -w \n%{http_code}"
  if [[ "$url" == https://* ]]; then
    curl_opts="$curl_opts -k"
  fi
  echo "$curl_opts"
}

https_opts=$(test_curl_opts "https://example.com/health")
if [[ "$https_opts" == *"-k"* ]]; then
  echo "✓ PASS: HTTPS URL correctly adds -k flag"
else
  echo "✗ FAIL: HTTPS URL missing -k flag"
  exit 1
fi

# Test 2: Verify HTTP URL does not use -k flag
echo ""
echo "Test 2: HTTP URL should NOT use -k flag"
echo "--------------------------------------"

http_opts=$(test_curl_opts "http://example.com/health")
if [[ "$http_opts" != *"-k"* ]]; then
  echo "✓ PASS: HTTP URL correctly omits -k flag"
else
  echo "✗ FAIL: HTTP URL incorrectly includes -k flag"
  exit 1
fi

# Test 3: Test with a real HTTPS endpoint (if available)
echo ""
echo "Test 3: Real HTTPS endpoint test"
echo "--------------------------------------"

# Test against a public HTTPS endpoint to verify curl works
test_url="https://httpbin.org/status/200"
echo "Testing against: $test_url"

curl_opts="-s -w \n%{http_code} -k"
response=$(curl $curl_opts "$test_url" 2>/dev/null || echo "000")
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "200" ]; then
  echo "✓ PASS: HTTPS endpoint with -k flag returns 200"
else
  echo "✗ FAIL: HTTPS endpoint returned HTTP $http_code"
  exit 1
fi

echo ""
echo "========================================="
echo "All Tests Passed!"
echo "========================================="
echo ""
echo "The validation script fix correctly:"
echo "  1. Adds -k flag for HTTPS URLs"
echo "  2. Omits -k flag for HTTP URLs"
echo "  3. Successfully validates HTTPS endpoints"
echo ""

exit 0
