#!/bin/bash

# ServiceNow-AWS Integration - One-Click Deployment Script
# This script deploys the complete system from scratch
###########################################
# Execute chmod +x deploy.sh before running
###########################################

set -e  # Exit on error

echo "=========================================="
echo "ServiceNow-AWS Integration Deployment"
echo "=========================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first."
    exit 1
fi

# Check jq
if ! command -v jq &> /dev/null; then
    echo "❌ jq not found. Please install it first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Run 'aws configure' first."
    exit 1
fi

echo "✅ Prerequisites met"
echo ""

# Get AWS account info
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "us-east-1")

echo "Deployment Configuration:"
echo "  AWS Account: $ACCOUNT_ID"
echo "  Region: $REGION"
echo ""

read -p "Continue with deployment? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "=========================================="
echo "Step 1: Deploy CloudFormation Stack"
echo "=========================================="

# Validate template
echo "Validating CloudFormation template..."
aws cloudformation validate-template \
  --template-body file://spa-creator-stack.yaml > /dev/null
echo "✅ Template is valid"

# Deploy stack
echo "Deploying stack (this takes 5-7 minutes)..."
aws cloudformation create-stack \
  --stack-name servicenow-spa-creator \
  --template-body file://spa-creator-stack.yaml \
  --parameters ParameterKey=EnvironmentName,ParameterValue=sandbox \
  --capabilities CAPABILITY_NAMED_IAM > /dev/null

aws cloudformation wait stack-create-complete \
  --stack-name servicenow-spa-creator

echo "✅ CloudFormation stack deployed"
echo ""

# Get endpoints
export SPA_CREATOR_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name servicenow-spa-creator \
  --query 'Stacks[0].Outputs[?OutputKey==`SPACreatorAPIEndpoint`].OutputValue' \
  --output text)

export BACKEND_API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name servicenow-spa-creator \
  --query 'Stacks[0].Outputs[?OutputKey==`BackendAPIEndpoint`].OutputValue' \
  --output text)

echo "API Endpoints:"
echo "  SPA Creator: $SPA_CREATOR_ENDPOINT"
echo "  Backend API: $BACKEND_API_ENDPOINT"
echo ""

# Save endpoints
cat > endpoints.sh << ENDPOINTS
export SPA_CREATOR_ENDPOINT="$SPA_CREATOR_ENDPOINT"
export BACKEND_API_ENDPOINT="$BACKEND_API_ENDPOINT"
ENDPOINTS
chmod +x endpoints.sh

echo "=========================================="
echo "Step 2: Deploy Lambda Functions"
echo "=========================================="

# SPA Creator
echo "Deploying SPA Creator Lambda..."
zip -q spa-creator-lambda.zip spa-creator-lambda.py
aws lambda update-function-code \
  --function-name sandbox-spa-creator \
  --zip-file fileb://spa-creator-lambda.zip > /dev/null
aws lambda update-function-configuration \
  --function-name sandbox-spa-creator \
  --handler spa-creator-lambda.lambda_handler > /dev/null
echo "✅ SPA Creator deployed"

# Backend functions
echo "Deploying Backend Lambda functions..."
zip -q backend-list-bucket.zip backend-list-bucket.py
aws lambda update-function-code \
  --function-name sandbox-backend-list-bucket \
  --zip-file fileb://backend-list-bucket.zip > /dev/null
aws lambda update-function-configuration \
  --function-name sandbox-backend-list-bucket \
  --handler backend-list-bucket.lambda_handler > /dev/null

zip -q backend-upload-url.zip backend-upload-url.py
aws lambda update-function-code \
  --function-name sandbox-backend-upload-url \
  --zip-file fileb://backend-upload-url.zip > /dev/null
aws lambda update-function-configuration \
  --function-name sandbox-backend-upload-url \
  --handler backend-upload-url.lambda_handler > /dev/null

zip -q backend-user-info.zip backend-user-info.py
aws lambda update-function-code \
  --function-name sandbox-backend-user-info \
  --zip-file fileb://backend-user-info.zip > /dev/null
aws lambda update-function-configuration \
  --function-name sandbox-backend-user-info \
  --handler backend-user-info.lambda_handler > /dev/null

echo "✅ All Lambda functions deployed"
echo ""

echo "=========================================="
echo "Step 3: Update IAM Permissions"
echo "=========================================="

export IAM_ROLE=$(aws lambda get-function-configuration \
  --function-name sandbox-spa-creator \
  --query 'Role' \
  --output text | awk -F'/' '{print $NF}')

echo "Updating IAM role: $IAM_ROLE"
aws iam put-role-policy \
  --role-name "$IAM_ROLE" \
  --policy-name SPACreatorPolicy \
  --policy-document file://spa-creator-policy.json

echo "✅ IAM permissions updated"
echo ""

echo "=========================================="
echo "Step 4: Testing Deployment"
echo "=========================================="

echo "Creating test SPA..."
RESPONSE=$(curl -s -X POST "$SPA_CREATOR_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{"username": "deployment.test"}')

SUCCESS=$(echo "$RESPONSE" | jq -r '.success')

if [ "$SUCCESS" == "true" ]; then
    echo "✅ Test SPA created successfully!"
    WEBSITE_URL=$(echo "$RESPONSE" | jq -r '.websiteUrl')
    echo ""
    echo "Test website URL: $WEBSITE_URL"
else
    echo "❌ Test failed. Response:"
    echo "$RESPONSE" | jq '.'
    exit 1
fi

echo ""
echo "=========================================="
echo "🎉 Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Run './test-complete-flow.sh' for comprehensive testing"
echo "  2. Read 'API-REFERENCE.md' for API documentation"
echo "  3. Read 'SERVICENOW-INTEGRATION.md' for ServiceNow setup"
echo "  4. Read 'DEMO-SCRIPT.md' for demo preparation"
echo ""
echo "Your endpoints (also saved in endpoints.sh):"
echo "  SPA Creator: $SPA_CREATOR_ENDPOINT"
echo "  Backend API: $BACKEND_API_ENDPOINT"
echo ""
echo "To reload endpoints in a new session:"
echo "  source endpoints.sh"
echo ""
