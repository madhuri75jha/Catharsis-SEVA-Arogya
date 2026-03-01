"""
AWS Connectivity Diagnostic Script
Run this to diagnose connection issues with AWS services
"""
import os
import sys
import boto3
from dotenv import load_dotenv
import socket
import urllib.request
import urllib.error

# Load environment variables
load_dotenv()

def test_dns_resolution():
    """Test if we can resolve AWS endpoints"""
    print("\n=== Testing DNS Resolution ===")
    endpoints = [
        "cognito-idp.ap-south-1.amazonaws.com",
        "s3.ap-south-1.amazonaws.com",
        "transcribe.ap-south-1.amazonaws.com"
    ]
    
    for endpoint in endpoints:
        try:
            ip = socket.gethostbyname(endpoint)
            print(f"✓ {endpoint} resolves to {ip}")
        except socket.gaierror as e:
            print(f"✗ {endpoint} - DNS resolution failed: {e}")
            return False
    return True

def test_http_connectivity():
    """Test if we can make HTTP connections to AWS"""
    print("\n=== Testing HTTP Connectivity ===")
    try:
        response = urllib.request.urlopen("https://cognito-idp.ap-south-1.amazonaws.com", timeout=5)
        print(f"✓ Can connect to Cognito endpoint (status: {response.status})")
        return True
    except urllib.error.HTTPError as e:
        # HTTP 400/403 means we connected successfully, just no valid request
        if e.code in [400, 403]:
            print(f"✓ Can connect to Cognito endpoint (HTTP {e.code} is expected without valid request)")
            return True
        print(f"✗ Cannot connect to Cognito endpoint: HTTP {e.code}")
        return False
    except urllib.error.URLError as e:
        print(f"✗ Cannot connect to Cognito endpoint: {e.reason}")
        return False
    except Exception as e:
        print(f"✗ Cannot connect to Cognito endpoint: {e}")
        return False

def test_aws_credentials():
    """Test if AWS credentials are configured"""
    print("\n=== Testing AWS Credentials ===")
    
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region = os.getenv('AWS_REGION')
    
    print(f"AWS_ACCESS_KEY_ID: {'✓ Set' if access_key else '✗ Not set'}")
    print(f"AWS_SECRET_ACCESS_KEY: {'✓ Set' if secret_key else '✗ Not set'}")
    print(f"AWS_REGION: {region if region else '✗ Not set'}")
    
    if not all([access_key, secret_key, region]):
        return False
    
    return True

def test_boto3_client():
    """Test if we can create a boto3 client"""
    print("\n=== Testing Boto3 Client Creation ===")
    
    region = os.getenv('AWS_REGION', 'ap-south-1')
    
    try:
        # Try with explicit credentials
        client = boto3.client(
            'cognito-idp',
            region_name=region,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        print(f"✓ Successfully created cognito-idp client in {region}")
        
        # Try a simple API call
        try:
            response = client.list_user_pools(MaxResults=1)
            print(f"✓ Successfully made API call to Cognito")
            return True
        except Exception as e:
            print(f"✗ API call failed: {e}")
            return False
            
    except Exception as e:
        print(f"✗ Failed to create client: {e}")
        return False

def check_proxy_settings():
    """Check if proxy settings might be interfering"""
    print("\n=== Checking Proxy Settings ===")
    
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY', 'no_proxy']
    found_proxy = False
    
    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            print(f"{var}: {value}")
            found_proxy = True
    
    if not found_proxy:
        print("No proxy environment variables found")
    else:
        print("\n⚠ Proxy settings detected. These might interfere with AWS connections.")
        print("Try unsetting them: unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy")

def main():
    print("=" * 60)
    print("AWS Connectivity Diagnostic Tool")
    print("=" * 60)
    
    # Run all tests
    dns_ok = test_dns_resolution()
    http_ok = test_http_connectivity()
    creds_ok = test_aws_credentials()
    check_proxy_settings()
    boto_ok = test_boto3_client()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if all([dns_ok, http_ok, creds_ok, boto_ok]):
        print("✓ All tests passed! AWS connectivity should work.")
    else:
        print("✗ Some tests failed. Please address the issues above.")
        print("\nCommon fixes:")
        print("1. Check your internet connection")
        print("2. Verify AWS credentials in .env file")
        print("3. Check firewall/antivirus settings")
        print("4. Try disabling VPN if active")
        print("5. Check if proxy settings are interfering")
        sys.exit(1)

if __name__ == "__main__":
    main()
