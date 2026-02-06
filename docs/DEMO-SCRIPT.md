# Demo Script - ServiceNow-AWS Integration

## Demo Flow (5-7 minutes)

### 1. Introduction (30 seconds)
"Today I'll show you how ServiceNow can dynamically provision AWS resources through a single API call, creating complete user environments with interactive dashboards."

### 2. Architecture Overview (1 minute)
Show diagram:
- ServiceNow → API Gateway → Lambda → S3/DynamoDB
- Explain: Secure, serverless, scalable

### 3. Create SPA via API (2 minutes)

**Step 1**: Call API from terminal
```bash
curl -X POST https://o2w0pmchff.execute-api.us-east-1.amazonaws.com/prod/create-user-spa \
  -H "Content-Type: application/json" \
  -d '{"username": "demo.user"}' | jq '.'
```

**Show response**: 
- Bucket created
- Website URL returned
- All in ~2 seconds

**Step 2**: Open website URL in browser

### 4. Demonstrate SPA Features (3 minutes)

**Show interactive dashboard**:
1. User info display (username, bucket, region)
2. Click "Refresh File List" → Shows index.html, error.html
3. Drag & drop a file → Upload works
4. Refresh list → New file appears

**Explain what happened**:
- Browser called backend API
- Got presigned POST URL
- Uploaded directly to S3
- No server management needed

### 5. ServiceNow Integration (1 minute)

**Show ServiceNow Flow Designer**:
- Catalog item triggers API call
- User receives dashboard URL
- All tracked in ServiceNow

**Use cases**:
- Employee onboarding workspaces
- Project file sharing
- Client demo environments

### 6. Cleanup Demo (30 seconds)
Show cleanup script:
```bash
./cleanup-resources.sh
```

---

## Key Talking Points

✅ **Single API Call** - Complete environment provisioned  
✅ **Secure** - IAM roles, presigned URLs, CORS configured  
✅ **Scalable** - Serverless architecture  
✅ **Cost-Effective** - Pay only for what you use  
✅ **Sandbox-Safe** - All resources prefixed and isolated  
✅ **ServiceNow-Ready** - Easy REST integration  

---

## Demo Variations

### Technical Audience
- Show Lambda code
- Explain presigned POST vs PUT
- Discuss CORS configuration
- Review IAM policies

### Business Audience
- Focus on use cases
- Show time savings
- Discuss cost benefits
- Emphasize security

### Hands-On Workshop
- Guide participants through setup
- Have them create their own SPAs
- Let them upload files
- Show ServiceNow integration
