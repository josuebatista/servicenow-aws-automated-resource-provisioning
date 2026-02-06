# ServiceNow-AWS Integration API Reference

## Base URLs
- **SPA Creator API**: https://o2w0pmchff.execute-api.us-east-1.amazonaws.com/prod
- **Backend API**: https://058g4uppkk.execute-api.us-east-1.amazonaws.com/prod

---

## SPA Creator API

### Create User SPA
Creates a complete S3 bucket with static website hosting and deploys an interactive dashboard.

**Endpoint**: `POST /create-user-spa`

**Request**:
```json
{
  "username": "john.doe"
}
```

**Response**:
```json
{
  "success": true,
  "username": "john.doe",
  "bucketName": "sandbox-spa-john-doe-a1b2c3d4",
  "websiteUrl": "http://sandbox-spa-john-doe-a1b2c3d4.s3-website-us-east-1.amazonaws.com",
  "apiEndpoint": "https://058g4uppkk.execute-api.us-east-1.amazonaws.com/prod",
  "region": "us-east-1",
  "createdAt": "2026-02-06T15:30:00.123456",
  "message": "SPA created successfully!"
}
```

**What It Creates**:
- S3 bucket with unique name
- Static website hosting enabled
- CORS configuration for uploads
- Public read policy
- Interactive HTML dashboard
- DynamoDB tracking record

---

## Backend APIs

### 1. List Bucket Contents
List all files in a user's S3 bucket.

**Endpoint**: `GET /bucket-contents?bucket={bucket-name}`

**Response**:
```json
{
  "success": true,
  "bucket": "sandbox-spa-john-doe-a1b2c3d4",
  "fileCount": 3,
  "files": [
    {
      "name": "index.html",
      "size": 11486,
      "lastModified": "2026-02-06T02:41:47+00:00",
      "url": "https://sandbox-spa-john-doe-a1b2c3d4.s3.amazonaws.com/index.html"
    }
  ]
}
```

### 2. Generate Upload URL
Generate presigned POST URL for secure file uploads.

**Endpoint**: `POST /upload-url`

**Request**:
```json
{
  "bucket": "sandbox-spa-john-doe-a1b2c3d4",
  "filename": "document.pdf",
  "contentType": "application/pdf"
}
```

**Response**:
```json
{
  "success": true,
  "uploadUrl": "https://sandbox-spa-john-doe-a1b2c3d4.s3.amazonaws.com/",
  "fields": {
    "key": "document.pdf",
    "x-amz-algorithm": "AWS4-HMAC-SHA256",
    "x-amz-credential": "...",
    "x-amz-date": "...",
    "x-amz-security-token": "...",
    "policy": "...",
    "x-amz-signature": "...",
    "Content-Type": "application/pdf"
  },
  "bucket": "sandbox-spa-john-doe-a1b2c3d4",
  "filename": "document.pdf",
  "expiresIn": 300,
  "method": "POST"
}
```

### 3. Get User Info
Retrieve user's resource information from DynamoDB.

**Endpoint**: `GET /user-info?username={username}`

**Response**:
```json
{
  "success": true,
  "username": "john.doe",
  "resourceCount": 2,
  "resources": [
    {
      "username": "john.doe",
      "createdAt": "2026-02-06T02:41:46.251627",
      "bucketName": "sandbox-spa-john-doe-a1b2c3d4",
      "websiteUrl": "http://sandbox-spa-john-doe-a1b2c3d4.s3-website-us-east-1.amazonaws.com",
      "region": "us-east-1",
      "environment": "sandbox",
      "status": "active"
    }
  ]
}
```

---

## Security Features

- **IAM Roles**: Lambda functions use least-privilege IAM roles
- **Bucket Scoping**: Only buckets with `sandbox-spa-` prefix are accessible
- **CORS**: Configured for secure browser uploads
- **Presigned URLs**: Time-limited (5 minutes) upload URLs
- **Public Access**: Limited to GetObject only (read-only for public)

---

## Resource Naming

- **Buckets**: `{environment}-spa-{sanitized-username}-{unique-id}`
- **Example**: `sandbox-spa-john-doe-a1b2c3d4`
- **DynamoDB Table**: `sandbox-spa-resources`
- **Lambda Functions**: 
  - `sandbox-spa-creator`
  - `sandbox-backend-list-bucket`
  - `sandbox-backend-upload-url`
  - `sandbox-backend-user-info`
