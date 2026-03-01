# AWS Connection Error Fix Guide

## Error
```
Could not connect to the endpoint URL: "https://cognito-idp.ap-south-1.amazonaws.com/"
```

## What I Fixed

1. **Updated `aws_services/base_client.py`**:
   - Now explicitly passes AWS credentials from environment variables to boto3
   - Added better error logging to diagnose connection issues
   - Added helpful error messages pointing to common causes

2. **Created `test_aws_connectivity.py`**:
   - Diagnostic script to test AWS connectivity
   - Checks DNS resolution, HTTP connectivity, credentials, and boto3 client creation

## How to Fix

### Step 1: Run the Diagnostic Script

```bash
python test_aws_connectivity.py
```

This will tell you exactly what's wrong.

### Step 2: Common Fixes

#### Fix 1: Check Internet Connection
- Make sure you have internet access
- Try pinging: `ping cognito-idp.ap-south-1.amazonaws.com`

#### Fix 2: Verify AWS Credentials in .env
Make sure your `.env` file has valid credentials:
```
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY
AWS_REGION=ap-south-1
```

#### Fix 3: Check Firewall/Antivirus
- Temporarily disable firewall/antivirus to test
- Add exception for Python and your app

#### Fix 4: Disable VPN
- Some VPNs block AWS endpoints
- Try disconnecting VPN temporarily

#### Fix 5: Check Proxy Settings
If you're behind a corporate proxy, unset proxy variables:

**Windows (PowerShell):**
```powershell
$env:HTTP_PROXY=""
$env:HTTPS_PROXY=""
$env:http_proxy=""
$env:https_proxy=""
```

**Windows (CMD):**
```cmd
set HTTP_PROXY=
set HTTPS_PROXY=
set http_proxy=
set https_proxy=
```

**Linux/Mac:**
```bash
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
```

#### Fix 6: Test with AWS CLI
Install AWS CLI and test:
```bash
aws cognito-idp list-user-pools --max-results 1 --region ap-south-1
```

If this works, your credentials are fine and it's a Python/boto3 issue.

### Step 3: Restart Your Application

After applying fixes:
```bash
python app.py
```

## What Changed in the Code

The `base_client.py` now explicitly passes credentials to boto3:

```python
# Before (relied on boto3's default credential chain)
self.client = boto3.client(service_name, region_name=region)

# After (explicitly passes credentials from environment)
self.client = boto3.client(
    service_name,
    region_name=region,
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)
```

This ensures credentials from your `.env` file are used directly.

## Still Not Working?

If the diagnostic script passes but you still get errors:

1. Check if boto3 is up to date:
   ```bash
   pip install --upgrade boto3 botocore
   ```

2. Clear Python cache:
   ```bash
   find . -type d -name __pycache__ -exec rm -rf {} +
   ```

3. Check your AWS credentials are valid:
   - Log into AWS Console
   - Go to IAM → Users → Your User → Security Credentials
   - Verify the access key is active
   - Create a new access key if needed

4. Verify the Cognito User Pool exists:
   - AWS Console → Cognito → User Pools
   - Check if `ap-south-1_rGtzTkqP9` exists in ap-south-1 region
