#!/bin/bash

# Cleanup Script for ServiceNow-AWS Integration Demo
# WARNING: This will DELETE all sandbox-spa-* resources

echo "========================================"
echo "ServiceNow-AWS Integration Cleanup"
echo "========================================"
echo ""

read -p "Are you sure you want to delete ALL sandbox-spa resources? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Starting cleanup..."
echo ""

# 1. List and delete all SPA buckets
echo "1. Finding SPA buckets..."
BUCKETS=$(aws s3 ls | grep sandbox-spa | awk '{print $3}')

if [ -z "$BUCKETS" ]; then
    echo "   No SPA buckets found"
else
    for bucket in $BUCKETS; do
        echo "   Deleting bucket: $bucket"
        # Delete all objects first
        aws s3 rm s3://$bucket --recursive --quiet
        # Delete bucket
        aws s3 rb s3://$bucket --force
    done
    echo "   ✅ All SPA buckets deleted"
fi

# 2. Clear DynamoDB table
echo ""
echo "2. Clearing DynamoDB table..."
TABLE_NAME="sandbox-spa-resources"

# Scan and delete all items
aws dynamodb scan --table-name $TABLE_NAME --query 'Items[*].[username.S, createdAt.S]' --output text | \
while read username createdAt; do
    if [ -n "$username" ]; then
        echo "   Deleting record: $username"
        aws dynamodb delete-item \
            --table-name $TABLE_NAME \
            --key "{\"username\": {\"S\": \"$username\"}, \"createdAt\": {\"S\": \"$createdAt\"}}"
    fi
done
echo "   ✅ DynamoDB table cleared"

# 3. Optional: Delete CloudFormation stack
echo ""
read -p "Delete the entire CloudFormation stack? (yes/no): " delete_stack

if [ "$delete_stack" == "yes" ]; then
    echo "   Deleting CloudFormation stack..."
    aws cloudformation delete-stack --stack-name servicenow-spa-creator
    echo "   ⏳ Waiting for stack deletion..."
    aws cloudformation wait stack-delete-complete --stack-name servicenow-spa-creator
    echo "   ✅ CloudFormation stack deleted"
fi

echo ""
echo "========================================"
echo "Cleanup Complete!"
echo "========================================"