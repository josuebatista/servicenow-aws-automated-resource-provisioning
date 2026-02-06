# ServiceNow-AWS Integration - Complete Deployment Guide

## Overview
This guide will walk you through deploying the complete ServiceNow-AWS SPA Creator system in any AWS account from scratch.

**Time to Deploy**: 15-20 minutes  
**Prerequisites**: AWS account with admin access, AWS CLI configured  
**Cost**: Minimal (< $5/month for typical usage)

---

## Architecture
```
ServiceNow → API Gateway → Lambda Functions → S3 Buckets + DynamoDB
                ↓
         SPA Creator API (creates resources)
                ↓
         Backend APIs (power interactive features)
```

**Resources Created**:
- 2 API Gateways (HTTP APIs)
- 4 Lambda Functions
- 1 DynamoDB Table
- 1 S3 Bucket (for Lambda code)
- Multiple user S3 buckets (created on-demand)
- 2 IAM Roles

---

## Prerequisites

### 1. AWS Account Setup
- AWS account with administrator access
- AWS CLI installed and configured
- `jq` installed (for JSON parsing)

### 2. Verify AWS CLI
```bash
aws sts get-caller-identity
```

You should see your account ID and user ARN.

### 3. Choose Region
```bash
# Set your deployment region
export AWS_DEFAULT_REGION=us-east-1

# Or change to your preferred region
# export AWS_DEFAULT_REGION=us-west-2
```

---

## Deployment Steps

### Step 1: Prepare Files

Create a deployment directory:
```bash
mkdir servicenow-aws-integration
cd servicenow-aws-integration
```

You should have these 10 files:
```
API-REFERENCE.md
backend-list-bucket.py
backend-upload-url.py
backend-user-info.py
cleanup-resources.sh
DEMO-SCRIPT.md
SERVICENOW-INTEGRATION.md
spa-creator-lambda.py
spa-creator-policy.json
spa-creator-stack.yaml
test-complete-flow.sh
```

### Step 2: Deploy CloudFormation Stack

**Deploy the infrastructure**:
```bash
# Validate the CloudFormation template
aws cloudformation validate-template \
  --template-body file://spa-creator-stack.yaml

# Deploy the stack
aws cloudformation create-stack \
  --stack-name servicenow-spa-creator \
  --template-body file://spa-creator-stack.yaml \
  --parameters ParameterKey=EnvironmentName,ParameterValue=sandbox \
  --capabilities CAPABILITY_NAMED_IAM

# Wait for completion (5-7 minutes)
echo "⏳ Waiting for stack creation..."
aws cloudformation wait stack-create-complete \
  --stack-name servicenow-spa-creator

echo "✅ Stack created successfully!"
```

**Verify deployment**:
```bash
# Check stack status
aws cloudformation describe-stacks \
  --stack-name servicenow-spa-creator \
  --query 'Stacks[0].StackStatus'

# Get outputs
aws cloudformation describe-stacks \
  --stack-name servicenow-spa-creator \
  --query 'Stacks[0].Outputs' \
  --output table
```

### Step 3: Save Endpoint URLs
```bash
# Save API endpoints to environment variables
export SPA_CREATOR_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name servicenow-spa-creator \
  --query 'Stacks[0].Outputs[?OutputKey==`SPACreatorAPIEndpoint`].OutputValue' \
  --output text)

export BACKEND_API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name servicenow-spa-creator \
  --query 'Stacks[0].Outputs[?OutputKey==`BackendAPIEndpoint`].OutputValue' \
  --output text)

# Display endpoints
echo "SPA Creator Endpoint: $SPA_CREATOR_ENDPOINT"
echo "Backend API Endpoint: $BACKEND_API_ENDPOINT"

# Save to file for future sessions
cat > endpoints.sh << ENDPOINTS
export SPA_CREATOR_ENDPOINT="$SPA_CREATOR_ENDPOINT"
export BACKEND_API_ENDPOINT="$BACKEND_API_ENDPOINT"
ENDPOINTS

chmod +x endpoints.sh
```

### Step 4: Deploy Lambda Functions

**Deploy SPA Creator Lambda**:
```bash
# Package the Lambda function
zip spa-creator-lambda.zip spa-creator-lambda.py

# Deploy
aws lambda update-function-code \
  --function-name sandbox-spa-creator \
  --zip-file fileb://spa-creator-lambda.zip

# Update handler
aws lambda update-function-configuration \
  --function-name sandbox-spa-creator \
  --handler spa-creator-lambda.lambda_handler

echo "✅ SPA Creator Lambda deployed"
```

**Deploy Backend Lambda Functions**:
```bash
# Backend 1: List Bucket
zip backend-list-bucket.zip backend-list-bucket.py
aws lambda update-function-code \
  --function-name sandbox-backend-list-bucket \
  --zip-file fileb://backend-list-bucket.zip
aws lambda update-function-configuration \
  --function-name sandbox-backend-list-bucket \
  --handler backend-list-bucket.lambda_handler
echo "✅ backend-list-bucket deployed"

# Backend 2: Upload URL
zip backend-upload-url.zip backend-upload-url.py
aws lambda update-function-code \
  --function-name sandbox-backend-upload-url \
  --zip-file fileb://backend-upload-url.zip
aws lambda update-function-configuration \
  --function-name sandbox-backend-upload-url \
  --handler backend-upload-url.lambda_handler
echo "✅ backend-upload-url deployed"

# Backend 3: User Info
zip backend-user-info.zip backend-user-info.py
aws lambda update-function-code \
  --function-name sandbox-backend-user-info \
  --zip-file fileb://backend-user-info.zip
aws lambda update-function-configuration \
  --function-name sandbox-backend-user-info \
  --handler backend-user-info.lambda_handler
echo "✅ backend-user-info deployed"

# Wait for all updates
sleep 10
```

### Step 5: Update IAM Permissions

The CloudFormation stack creates the IAM roles, but we need to ensure the SPA Creator has the `s3:PutBucketCors` permission:
```bash
# Get the IAM role name
export IAM_ROLE=$(aws lambda get-function-configuration \
  --function-name sandbox-spa-creator \
  --query 'Role' \
  --output text | awk -F'/' '{print $NF}')

echo "IAM Role: $IAM_ROLE"

# Update the policy with CORS permission
aws iam put-role-policy \
  --role-name "$IAM_ROLE" \
  --policy-name SPACreatorPolicy \
  --policy-document file://spa-creator-policy.json

echo "✅ IAM permissions updated"

# Verify
aws iam get-role-policy \
  --role-name "$IAM_ROLE" \
  --policy-name SPACreatorPolicy \
  --query 'PolicyDocument.Statement[0].Action' | grep -q "s3:PutBucketCors" && echo "✅ CORS permission confirmed"
```

### Step 6: Update Configuration Files

Update the test script with your endpoints:
```bash
# Update test script
sed -i.bak "s|SPA_CREATOR_ENDPOINT=.*|SPA_CREATOR_ENDPOINT=\"$SPA_CREATOR_ENDPOINT\"|" test-complete-flow.sh
sed -i.bak "s|BACKEND_API_ENDPOINT=.*|BACKEND_API_ENDPOINT=\"$BACKEND_API_ENDPOINT\"|" test-complete-flow.sh

echo "✅ Configuration files updated"
```

---

## Testing the Deployment

### Quick Test
```bash
# Test creating a SPA
curl -X POST "$SPA_CREATOR_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{"username": "test.user"}' | jq '.'
```

Expected response:
```json
{
  "success": true,
  "username": "test.user",
  "bucketName": "sandbox-spa-test-user-XXXXXXXX",
  "websiteUrl": "http://sandbox-spa-test-user-XXXXXXXX.s3-website-us-east-1.amazonaws.com",
  ...
}
```

### Complete Test Suite
```bash
# Run the automated test suite
./test-complete-flow.sh
```

This will test:
- ✅ SPA creation
- ✅ Bucket listing
- ✅ Upload URL generation
- ✅ User info retrieval
- ✅ CORS configuration

### Manual Browser Test
1. Create a SPA using the API
2. Open the returned `websiteUrl` in your browser
3. Click "Refresh File List" - should show 2 files
4. Drag & drop a file - should upload successfully
5. Refresh list - new file should appear

---

## Deployment Checklist

- [ ] CloudFormation stack deployed successfully
- [ ] All 4 Lambda functions deployed
- [ ] IAM permissions include `s3:PutBucketCors`
- [ ] API endpoints saved to `endpoints.sh`
- [ ] Quick test passes (SPA creation works)
- [ ] Complete test suite passes
- [ ] Browser test successful (upload works)
- [ ] Documentation reviewed

---

## Troubleshooting

### Issue: "Stack already exists"
**Solution**: Delete the existing stack first:
```bash
aws cloudformation delete-stack --stack-name servicenow-spa-creator
aws cloudformation wait stack-delete-complete --stack-name servicenow-spa-creator
```

### Issue: Lambda shows placeholder code
**Problem**: Lambda code not updated  
**Solution**: Redeploy Lambda functions (Step 4)

### Issue: Upload fails with CORS error
**Problem**: Missing `s3:PutBucketCors` permission  
**Solution**: Run Step 5 again to update IAM policy

### Issue: "AccessDenied" when creating SPA
**Problem**: IAM role missing permissions  
**Solution**: Verify policy file contains all required S3 actions:
```bash
cat spa-creator-policy.json | jq '.Statement[0].Action'
```

### Issue: API returns 404
**Problem**: API Gateway not deployed  
**Solution**: Verify CloudFormation outputs:
```bash
aws cloudformation describe-stacks \
  --stack-name servicenow-spa-creator \
  --query 'Stacks[0].Outputs'
```

---

## Region-Specific Notes

### Deploying to Non-US-East-1 Regions

If deploying to a region other than `us-east-1`, update:

**CloudFormation template**:
```yaml
# No changes needed - template uses AWS::Region automatically
```

**S3 bucket creation** (in Lambda):
```python
# Already handles all regions correctly
if AWS_REGION == 'us-east-1':
    s3.create_bucket(Bucket=bucket_name)
else:
    s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
    )
```

**Website URLs** will automatically use correct regional endpoint:
- us-east-1: `http://bucket.s3-website-us-east-1.amazonaws.com`
- us-west-2: `http://bucket.s3-website-us-west-2.amazonaws.com`
- eu-west-1: `http://bucket.s3-website-eu-west-1.amazonaws.com`

---

## Cost Estimation

**Monthly Costs** (assuming 100 SPA creations, 1000 file uploads):

| Service | Usage | Cost |
|---------|-------|------|
| API Gateway | 1,100 requests | $0.00 (free tier) |
| Lambda | 1,100 invocations | $0.00 (free tier) |
| S3 Storage | 10 GB | $0.23 |
| S3 Requests | 1,100 | $0.01 |
| DynamoDB | 100 writes, on-demand | $0.25 |
| **Total** | | **~$0.50/month** |

**Free Tier Benefits**:
- Lambda: 1M free requests/month
- API Gateway: 1M free requests/month (first 12 months)
- S3: 5GB free storage (first 12 months)

---

## Cleanup

When done testing, clean up all resources:
```bash
# Option 1: Clean up user-created resources only
./cleanup-resources.sh

# Option 2: Delete everything including infrastructure
aws cloudformation delete-stack --stack-name servicenow-spa-creator
aws cloudformation wait stack-delete-complete --stack-name servicenow-spa-creator
```

---

## Next Steps

After successful deployment:

1. **Review API Documentation**: See `API-REFERENCE.md`
2. **ServiceNow Integration**: See `SERVICENOW-INTEGRATION.md`
3. **Demo Preparation**: See `DEMO-SCRIPT.md`
4. **Production Hardening**: See "Production Considerations" below

---

## Production Considerations

Before deploying to production:

### Security Enhancements
1. **Add API Key Authentication**:
   - Configure API Gateway with API keys
   - Distribute keys securely to ServiceNow

2. **Restrict IP Access**:
   - Use API Gateway resource policies
   - Allow only ServiceNow IP ranges

3. **Enable CloudTrail**:
   - Log all API calls
   - Monitor for unauthorized access

4. **Encrypt Data**:
   - Enable S3 bucket encryption (AES-256)
   - Use KMS for sensitive data

### Monitoring & Alerting
1. **CloudWatch Alarms**:
   - Lambda errors > threshold
   - API Gateway 4xx/5xx errors
   - DynamoDB throttling

2. **CloudWatch Dashboards**:
   - API request counts
   - Lambda duration/errors
   - S3 bucket usage

3. **X-Ray Tracing**:
   - Enable for Lambda functions
   - Trace request flow

### Scaling & Performance
1. **Lambda Concurrency**:
   - Set reserved concurrency if needed
   - Monitor concurrent executions

2. **API Gateway Throttling**:
   - Configure rate limits
   - Implement burst handling

3. **S3 Performance**:
   - Use Transfer Acceleration for large files
   - Implement lifecycle policies

### Backup & Recovery
1. **DynamoDB Backups**:
   - Enable point-in-time recovery
   - Schedule daily backups

2. **S3 Versioning**:
   - Enable for accidental deletion protection
   - Configure lifecycle to clean old versions

3. **Infrastructure as Code**:
   - Store CloudFormation template in version control
   - Automate deployment with CI/CD

---

## Support & Resources

**AWS Documentation**:
- API Gateway: https://docs.aws.amazon.com/apigateway/
- Lambda: https://docs.aws.amazon.com/lambda/
- S3: https://docs.aws.amazon.com/s3/

**ServiceNow Documentation**:
- REST Message: https://docs.servicenow.com/
- Flow Designer: https://docs.servicenow.com/

**This Project**:
- API Reference: `API-REFERENCE.md`
- ServiceNow Integration: `SERVICENOW-INTEGRATION.md`
- Demo Script: `DEMO-SCRIPT.md`
