# ServiceNow Integration Guide

## Overview
This guide shows how to integrate the AWS SPA Creator into ServiceNow to dynamically provision user resources.

---

## Integration Approach

### Option 1: Catalog Item with REST API Call

**Use Case**: Self-service portal for users to request personal AWS dashboards

**Steps**:
1. Create a Service Catalog item in ServiceNow
2. Add a REST Message to call the SPA Creator API
3. Use Flow Designer to orchestrate the workflow
4. Return the website URL to the user

**ServiceNow REST Message Configuration**:
```
Name: AWS_SPA_Creator
Endpoint: https://o2w0pmchff.execute-api.us-east-1.amazonaws.com/prod/create-user-spa
HTTP Method: POST
HTTP Headers: 
  - Content-Type: application/json
Authentication: None (or API Key if you add one)

HTTP Body:
{
  "username": "${username}"
}
```

### Option 2: AI Agent Tool

**Use Case**: Conversational interface for creating resources

**ServiceNow Agent Tool Configuration**:
```javascript
// Tool: Create AWS Dashboard
// Description: Creates a personal AWS dashboard for a user

var request = new sn_ws.RESTMessageV2();
request.setEndpoint('https://o2w0pmchff.execute-api.us-east-1.amazonaws.com/prod/create-user-spa');
request.setHttpMethod('POST');
request.setRequestHeader('Content-Type', 'application/json');

var body = {
    username: input.username
};
request.setRequestBody(JSON.stringify(body));

var response = request.execute();
var responseBody = JSON.parse(response.getBody());

return {
    success: responseBody.success,
    websiteUrl: responseBody.websiteUrl,
    bucketName: responseBody.bucketName
};
```

### Option 3: Flow Designer Integration

**Flow Steps**:

1. **Trigger**: Catalog item submitted
2. **Action**: REST - POST to SPA Creator API
3. **Condition**: Check if success = true
4. **Action**: Send notification with website URL
5. **Action**: Create record in CMDB (optional)

**Sample Flow Designer REST Action**:
```
Connection: AWS_SPA_Creator
Resource Path: /create-user-spa
HTTP Method: POST
Request Body:
{
  "username": "${catalog_item.variables.user_email}"
}
```

---

## Example Use Cases

### 1. Employee Onboarding
- New employee submits onboarding form
- ServiceNow creates personal AWS workspace
- Employee receives dashboard URL via email
- Files uploaded during onboarding stored in personal bucket

### 2. Project Provisioning
- Team requests project workspace
- ServiceNow creates shared bucket/dashboard
- Team members can upload project files
- All resources tracked in ServiceNow CMDB

### 3. Client Demos
- Sales creates demo environment for client
- Client gets personalized dashboard
- Sales can show real AWS resource creation
- Environment auto-tracked for cleanup

---

## Sample ServiceNow Script
```javascript
// Catalog Item Script
(function() {
    var username = current.variables.username.toString();
    
    // Call AWS API
    var request = new sn_ws.RESTMessageV2();
    request.setEndpoint('https://o2w0pmchff.execute-api.us-east-1.amazonaws.com/prod/create-user-spa');
    request.setHttpMethod('POST');
    request.setRequestHeader('Content-Type', 'application/json');
    request.setRequestBody(JSON.stringify({username: username}));
    
    var response = request.execute();
    var httpStatus = response.getStatusCode();
    
    if (httpStatus == 200) {
        var result = JSON.parse(response.getBody());
        
        // Store in catalog variables
        current.variables.website_url = result.websiteUrl;
        current.variables.bucket_name = result.bucketName;
        current.update();
        
        gs.info('AWS Dashboard created: ' + result.websiteUrl);
        return result.websiteUrl;
    } else {
        gs.error('Failed to create AWS dashboard: ' + response.getBody());
        return null;
    }
})();
```

---

## Best Practices

1. **Username Sanitization**: Already handled by Lambda (lowercase, alphanumeric, hyphens)
2. **Error Handling**: Check `success` field in response
3. **URL Storage**: Store `websiteUrl` in ServiceNow for reference
4. **Resource Tracking**: Use `bucketName` for CMDB entries
5. **Cleanup**: Implement decommissioning process to delete buckets

---

## Testing from ServiceNow

### Quick Test Script
Run in ServiceNow Scripts - Background:
```javascript
var request = new sn_ws.RESTMessageV2();
request.setEndpoint('https://o2w0pmchff.execute-api.us-east-1.amazonaws.com/prod/create-user-spa');
request.setHttpMethod('POST');
request.setRequestHeader('Content-Type', 'application/json');
request.setRequestBody(JSON.stringify({
    username: 'test.user.' + new Date().getTime()
}));

var response = request.execute();
gs.info('Status: ' + response.getStatusCode());
gs.info('Response: ' + response.getBody());
```
