# AWS Connectivity Testing - Quick Reference

## 🚀 Deploy with Testing

```bash
./deploy_to_aws.sh
```

Automatically runs:
1. Pre-deployment checks (local connectivity)
2. Deployment (Terraform + Docker + ECS)
3. Post-deployment validation (remote connectivity)

## 🧪 Manual Tests

### Test Everything
```bash
python test_aws_connectivity.py
```

### Test Cognito Only
```bash
python test_cognito_connection.py
```

### Validate Deployment
```bash
cd seva-arogya-infra
API_URL=$(terraform output -raw api_base_url)
bash scripts/validate_deployment.sh "$API_URL"
```

## 🏥 Health Endpoints

### Basic Health
```bash
curl http://your-alb-url/health
```
Checks: Database, migrations, secrets manager

### AWS Connectivity
```bash
curl http://your-alb-url/health/aws-connectivity
```
Checks: Cognito, S3, Transcribe, Comprehend, Secrets Manager

## ⚡ Quick Fixes

### "Cannot connect to endpoint URL"
```bash
# Run diagnostic
python test_aws_connectivity.py

# Check output for specific issue
# Fix based on error message
```

### "Pre-deployment checks failed"
- Check internet connection
- Verify AWS credentials in `.env`
- Disable VPN temporarily
- Check firewall settings

### "Post-deployment validation timeout"
- Wait 2-3 minutes and retry
- Check NAT gateway is "available"
- Verify security groups allow outbound HTTPS
- Check ECS task logs

## 📁 Key Files

| File | Purpose |
|------|---------|
| `test_aws_connectivity.py` | Comprehensive diagnostic tool |
| `test_cognito_connection.py` | Quick Cognito test |
| `scripts/pre_deploy_check.sh` | Pre-deployment validation |
| `scripts/validate_deployment.sh` | Post-deployment validation |
| `deploy_to_aws.sh` | Main deployment script |
| `aws_services/connectivity_checker.py` | Connectivity checker class |

## 📚 Documentation

| Document | Content |
|----------|---------|
| `QUICK_START_TESTING.md` | Quick start guide |
| `DEPLOYMENT_TESTING.md` | Complete testing guide |
| `AWS_CONNECTION_FIX.md` | Troubleshooting guide |
| `DEPLOYMENT_TIMEOUT_FIX.md` | Timeout issue solutions |
| `FINAL_SUMMARY.md` | Complete summary |

## ✅ Success Output

```bash
==> Step 1: Basic Health Check
  ✓ Basic Health is healthy (HTTP 200)

==> Step 2: AWS Connectivity Check
  ✓ AWS Connectivity is healthy (HTTP 200)

✓ Deployment Validation Successful
```

## 🔍 Troubleshooting Commands

### Check ECS Logs
```bash
aws logs tail "/ecs/seva-arogya-dev" --follow --region ap-south-1
```

### Check NAT Gateway Status
```bash
aws ec2 describe-nat-gateways --region ap-south-1 \
  --filter "Name=tag:Project,Values=seva-arogya"
```

### Check Security Groups
```bash
aws ec2 describe-security-groups --region ap-south-1 \
  --filters "Name=tag:Project,Values=seva-arogya"
```

## 🎯 What Was Fixed

✅ Original error: "Could not connect to endpoint URL"  
✅ Added: Pre-deployment validation  
✅ Added: Post-deployment validation  
✅ Added: `/health/aws-connectivity` endpoint  
✅ Added: Comprehensive diagnostic tools  
✅ Added: CI/CD workflow  
✅ Fixed: Timeout handling (90s wait)  

## 💡 Pro Tips

1. **Always run pre-deployment checks** - Catches issues early
2. **Monitor health endpoints** - Set up CloudWatch alarms
3. **Check logs first** - Most issues show up in CloudWatch logs
4. **Wait for NAT gateway** - Takes 1-2 minutes to be ready
5. **Use VPC endpoints** - Better performance, lower cost

## 🆘 Need Help?

1. Check `DEPLOYMENT_TESTING.md` for detailed guides
2. Review `AWS_CONNECTION_FIX.md` for common issues
3. Run diagnostic scripts for specific error messages
4. Check CloudWatch logs for application errors

---

**Quick Deploy**: `./deploy_to_aws.sh`  
**Quick Test**: `python test_aws_connectivity.py`  
**Quick Validate**: `bash scripts/validate_deployment.sh <API_URL>`
