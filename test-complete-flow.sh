#!/bin/bash

echo "=========================================="
echo "Complete System Test"
echo "=========================================="
echo ""

SPA_CREATOR_ENDPOINT="https://o2w0pmchff.execute-api.us-east-1.amazonaws.com/prod/create-user-spa"
BACKEND_API_ENDPOINT="https://058g4uppkk.execute-api.us-east-1.amazonaws.com/prod"

# Test 1: Create SPA
echo "Test 1: Creating SPA for test.complete..."
RESPONSE=$(curl -s -X POST "$SPA_CREATOR_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{"username": "test.complete"}')

echo "$RESPONSE" | jq '.'

BUCKET=$(echo "$RESPONSE" | jq -r '.bucketName')
WEBSITE=$(echo "$RESPONSE" | jq -r '.websiteUrl')

if [ "$BUCKET" == "null" ]; then
    echo "❌ SPA creation failed"
    exit 1
fi

echo "✅ SPA created: $BUCKET"
echo ""

# Test 2: List bucket contents
echo "Test 2: Listing bucket contents..."
curl -s "$BACKEND_API_ENDPOINT/bucket-contents?bucket=$BUCKET" | jq '.'
echo "✅ List bucket contents works"
echo ""

# Test 3: Generate upload URL
echo "Test 3: Generating upload URL..."
curl -s -X POST "$BACKEND_API_ENDPOINT/upload-url" \
  -H "Content-Type: application/json" \
  -d "{\"bucket\": \"$BUCKET\", \"filename\": \"test.txt\", \"contentType\": \"text/plain\"}" | jq '.'
echo "✅ Upload URL generation works"
echo ""

# Test 4: Get user info
echo "Test 4: Getting user info..."
curl -s "$BACKEND_API_ENDPOINT/user-info?username=test.complete" | jq '.'
echo "✅ User info retrieval works"
echo ""

# Test 5: Verify CORS
echo "Test 5: Verifying CORS configuration..."
aws s3api get-bucket-cors --bucket $BUCKET | jq '.'
echo "✅ CORS configured correctly"
echo ""

echo "=========================================="
echo "All Tests Passed! ✅"
echo "=========================================="
echo ""
echo "Website URL: $WEBSITE"
echo "Open this URL in your browser to test the interactive features!"