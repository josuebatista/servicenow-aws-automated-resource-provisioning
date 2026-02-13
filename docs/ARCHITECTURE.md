# ServiceNow-AWS Automated Resource Provisioning Architecture

## Overview

This document describes the technical architecture of the ServiceNow-AWS integration system that enables dynamic provisioning of AWS resources through API-driven automation.

---

## High-Level Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Business Layer                           │
│         ServiceNow Platform (Workflow Orchestration)        │
│  • Service Catalog Items                                    │
│  • Flow Designer Workflows                                  │
│  • AI Agents / Virtual Agents                              │
│  • Integration Hub                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTPS REST API Call
                       │ (JSON Payload)
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Integration Layer                          │
│              AWS API Gateway (HTTP API)                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  SPA Creator API                                    │   │
│  │  POST /create-user-spa                              │   │
│  │  • CORS Enabled                                     │   │
│  │  • No Authentication (POC)                          │   │
│  │  • JSON Request/Response                            │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Backend API                                        │   │
│  │  GET  /bucket-contents?bucket={name}               │   │
│  │  POST /upload-url                                   │   │
│  │  GET  /user-info?username={name}                   │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Lambda Proxy Integration
                       │ (Event-Driven Invocation)
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Compute Layer                             │
│              AWS Lambda Functions (Python 3.11)             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  SPA Creator Function (sandbox-spa-creator)         │   │
│  │  • Orchestrates resource creation                   │   │
│  │  • Creates S3 buckets                               │   │
│  │  • Configures static website hosting                │   │
│  │  • Sets CORS policies                               │   │
│  │  • Generates and deploys HTML/CSS/JS                │   │
│  │  • Records metadata in DynamoDB                     │   │
│  │  Timeout: 300s | Memory: 512MB                      │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Backend Functions                                   │   │
│  │  • List Bucket (sandbox-backend-list-bucket)        │   │
│  │  • Upload URL (sandbox-backend-upload-url)          │   │
│  │  • User Info (sandbox-backend-user-info)            │   │
│  │  Timeout: 30s | Memory: 256MB                       │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ AWS SDK (boto3)
                       │ API Calls
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                Storage & Data Layer                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Amazon S3                                          │   │
│  │  • User buckets (sandbox-spa-{username}-{uuid})     │   │
│  │  • Static website hosting enabled                   │   │
│  │  • CORS configured for browser uploads              │   │
│  │  • Public read policy                               │   │
│  │  • Contains: index.html, error.html, user files    │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Amazon DynamoDB (sandbox-spa-resources)            │   │
│  │  • Partition Key: username                          │   │
│  │  • Sort Key: createdAt (ISO timestamp)              │   │
│  │  • Attributes: bucketName, websiteUrl, region,      │   │
│  │                environment, status                   │   │
│  │  • Billing: Pay-per-request (on-demand)             │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Amazon CloudWatch                                   │   │
│  │  • Lambda execution logs                            │   │
│  │  • API Gateway access logs                          │   │
│  │  • Metrics and monitoring                           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. API Gateway Layer

#### SPA Creator API
- **Type**: HTTP API (not REST API - lower latency, lower cost)
- **Protocol**: HTTPS
- **Endpoint**: `POST /create-user-spa`
- **Stage**: `prod` (auto-deploy enabled)
- **CORS**: Enabled (`*` for all origins)
- **Integration**: Lambda Proxy (payload format 2.0)
- **Timeout**: Inherits from Lambda (300s)

**Request Format**:
```json
{
  "username": "john.doe"
}
```

**Response Format**:
```json
{
  "success": true,
  "username": "john.doe",
  "bucketName": "sandbox-spa-john-doe-a1b2c3d4",
  "websiteUrl": "http://sandbox-spa-john-doe-a1b2c3d4.s3-website-us-east-1.amazonaws.com",
  "apiEndpoint": "https://{api-id}.execute-api.us-east-1.amazonaws.com/prod",
  "region": "us-east-1",
  "createdAt": "2026-02-06T15:30:00.123456",
  "message": "SPA created successfully!"
}
```

#### Backend API
- **Type**: HTTP API
- **Endpoints**:
  - `GET /bucket-contents?bucket={name}` - List S3 objects
  - `POST /upload-url` - Generate presigned POST URL
  - `GET /user-info?username={name}` - Query DynamoDB
- **Stage**: `prod`
- **CORS**: Enabled (required for browser uploads)
- **Integration**: Lambda Proxy for each endpoint

---

### 2. Lambda Functions Layer

#### SPA Creator Function
**Runtime**: Python 3.11  
**Handler**: `spa-creator-lambda.lambda_handler`  
**Timeout**: 300 seconds  
**Memory**: 512 MB  
**Role**: Custom IAM role with S3, DynamoDB permissions

**Execution Flow**:
1. Parse and validate username from request
2. Sanitize username (lowercase, alphanumeric, hyphens)
3. Generate unique bucket name with UUID suffix
4. Create S3 bucket (region-aware)
5. Configure static website hosting
6. Apply CORS configuration
7. Set public read bucket policy
8. Generate HTML/CSS/JavaScript for SPA
9. Upload `index.html` and `error.html` to S3
10. Record metadata in DynamoDB
11. Return success response with website URL

**IAM Permissions Required**:
- `s3:CreateBucket`
- `s3:PutBucketWebsite`
- `s3:PutBucketPolicy`
- `s3:PutBucketPublicAccessBlock`
- `s3:PutBucketCors`
- `s3:PutBucketTagging`
- `s3:PutObject`
- `s3:PutObjectAcl`
- `dynamodb:PutItem`

#### Backend List Bucket Function
**Runtime**: Python 3.11  
**Handler**: `backend-list-bucket.lambda_handler`  
**Timeout**: 30 seconds  
**Memory**: 256 MB

**Purpose**: Lists all objects in a specified S3 bucket

**Security**: Validates bucket name starts with `sandbox-spa-` prefix

**Returns**: Array of objects with name, size, lastModified, url

#### Backend Upload URL Function
**Runtime**: Python 3.11  
**Handler**: `backend-upload-url.lambda_handler`  
**Timeout**: 30 seconds  
**Memory**: 256 MB

**Purpose**: Generates presigned POST URL for browser-based S3 uploads

**Method**: Uses `s3.generate_presigned_post()` to create secure upload form

**Expiration**: 300 seconds (5 minutes)

**Returns**: Upload URL and form fields (including security credentials)

#### Backend User Info Function
**Runtime**: Python 3.11  
**Handler**: `backend-user-info.lambda_handler`  
**Timeout**: 30 seconds  
**Memory**: 256 MB

**Purpose**: Queries DynamoDB for user's resource metadata

**Query**: Uses DynamoDB Query operation on username partition key

**Returns**: Array of user's resources with metadata

---

### 3. Storage Layer

#### S3 Buckets

**Naming Convention**: `{environment}-spa-{sanitized-username}-{8-char-uuid}`  
**Example**: `sandbox-spa-john-doe-a1b2c3d4`

**Configuration**:
- **Region**: us-east-1 (or deployment region)
- **Versioning**: Disabled (not required for POC)
- **Encryption**: Server-side (AES-256, default)
- **Public Access**: Enabled for GetObject only
- **Static Website Hosting**: Enabled
  - Index document: `index.html`
  - Error document: `error.html`

**CORS Configuration**:
```json
{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "POST", "PUT", "HEAD"],
      "AllowedHeaders": ["*"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }
  ]
}
```

**Bucket Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::{bucket-name}/*"
    }
  ]
}
```

**Website Endpoint Format**:
- `http://{bucket-name}.s3-website-{region}.amazonaws.com`

**Tagging**:
- `Environment`: sandbox
- `Purpose`: User SPA
- `ManagedBy`: ServiceNow-AWS-Integration

#### DynamoDB Table

**Table Name**: `sandbox-spa-resources`  
**Billing Mode**: Pay-per-request (on-demand)

**Schema**:
```
Partition Key: username (String)
Sort Key: createdAt (String, ISO 8601 timestamp)

Attributes:
- username (String) - Primary key
- createdAt (String) - Sort key, ISO timestamp
- bucketName (String) - S3 bucket name
- websiteUrl (String) - Full website URL
- region (String) - AWS region
- environment (String) - Deployment environment
- status (String) - "active" or "deleted"
```

**Indexes**: None (simple table structure)

**Item Example**:
```json
{
  "username": "john.doe",
  "createdAt": "2026-02-06T15:30:00.123456",
  "bucketName": "sandbox-spa-john-doe-a1b2c3d4",
  "websiteUrl": "http://sandbox-spa-john-doe-a1b2c3d4.s3-website-us-east-1.amazonaws.com",
  "region": "us-east-1",
  "environment": "sandbox",
  "status": "active"
}
```

---

## Security Architecture

### 1. IAM Roles & Policies

#### SPA Creator Lambda Role
**Principle**: Least privilege access

**Permissions**:
- S3: Create and configure buckets matching `sandbox-spa-*` pattern only
- DynamoDB: Write to `sandbox-spa-resources` table only
- CloudWatch: Write logs to Lambda log groups

**Trust Policy**: Allows Lambda service to assume role

#### Backend API Lambda Role
**Permissions**:
- S3: Read/write/list on `sandbox-spa-*` buckets only
- IAM: Read user information (for user-info endpoint)
- DynamoDB: Read from `sandbox-spa-resources` table only
- CloudWatch: Write logs

### 2. Network Security

**API Gateway**:
- HTTPS only (TLS 1.2+)
- No VPC integration (publicly accessible)
- Optional: Resource policies for IP whitelisting (production)

**Lambda**:
- No VPC attachment (no VPC networking overhead)
- Communicates with AWS services via AWS PrivateLink
- Isolated execution environments

**S3**:
- Public read for GetObject only (website hosting)
- No public write access
- Uploads via presigned URLs only

### 3. Data Security

**Encryption at Rest**:
- S3: AES-256 server-side encryption (default)
- DynamoDB: Encryption at rest enabled by default
- Lambda: Ephemeral storage encrypted

**Encryption in Transit**:
- API Gateway: TLS 1.2+
- S3: HTTPS for all API operations
- DynamoDB: HTTPS for all operations

**Access Control**:
- Bucket-level policies (no object-level ACLs)
- Presigned URLs with time-based expiration (5 minutes)
- No permanent credentials exposed to clients

### 4. CORS Security

**Purpose**: Allow browser-based applications to upload files to S3

**Configuration**:
- Scoped to specific HTTP methods (GET, POST, PUT, HEAD)
- AllowedOrigins set to `*` (POC only - restrict in production)
- Exposes ETag header for upload verification
- 3000 second cache duration

---

## Data Flow Diagrams

### Flow 1: SPA Creation
```
┌──────────┐
│ServiceNow│
└────┬─────┘
     │
     │ 1. POST /create-user-spa
     │    {"username": "john.doe"}
     │
     ▼
┌─────────────┐
│ API Gateway │
└─────┬───────┘
      │
      │ 2. Invoke Lambda (Proxy Integration)
      │
      ▼
┌──────────────┐
│ SPA Creator  │
│   Lambda     │
└──┬───┬───┬───┘
   │   │   │
   │   │   │ 3. Create bucket
   │   │   └──────────────────┐
   │   │                      ▼
   │   │                 ┌────────┐
   │   │                 │   S3   │
   │   │                 └────────┘
   │   │                      │
   │   │ 4. Upload SPA files  │
   │   └──────────────────────┘
   │
   │ 5. Record metadata
   │
   ▼
┌──────────┐
│ DynamoDB │
└──────────┘
   │
   │ 6. Return success response
   │
   ▼
┌──────────┐
│ServiceNow│
└──────────┘
```

### Flow 2: File Upload from Browser
```
┌─────────┐
│ Browser │
│  (SPA)  │
└────┬────┘
     │
     │ 1. POST /upload-url
     │    {"bucket": "...", "filename": "..."}
     │
     ▼
┌─────────────┐
│Backend API  │
│  Gateway    │
└─────┬───────┘
      │
      │ 2. Invoke Lambda
      │
      ▼
┌──────────────┐
│Upload URL    │
│  Lambda      │
└──────┬───────┘
       │
       │ 3. generate_presigned_post()
       │
       ▼
   ┌────────┐
   │   S3   │
   └────┬───┘
        │
        │ 4. Return presigned URL + fields
        │
        ▼
   ┌─────────┐
   │ Browser │
   └────┬────┘
        │
        │ 5. POST multipart/form-data
        │    directly to S3
        │
        ▼
   ┌────────┐
   │   S3   │
   │ (file  │
   │ stored)│
   └────────┘
```

---

## Infrastructure as Code

### CloudFormation Stack

**Stack Name**: `servicenow-spa-creator`

**Resources Created**:
1. IAM Roles (2)
   - SPA Creator Lambda execution role
   - Backend API Lambda execution role

2. Lambda Functions (4)
   - `sandbox-spa-creator`
   - `sandbox-backend-list-bucket`
   - `sandbox-backend-upload-url`
   - `sandbox-backend-user-info`

3. API Gateways (2)
   - SPA Creator API (HTTP API)
   - Backend API (HTTP API)

4. API Gateway Stages (2)
   - `prod` for SPA Creator
   - `prod` for Backend API

5. API Gateway Integrations (4)
   - One per Lambda function

6. API Gateway Routes (4)
   - POST /create-user-spa
   - GET /bucket-contents
   - POST /upload-url
   - GET /user-info

7. Lambda Permissions (4)
   - Allow API Gateway to invoke each Lambda

8. DynamoDB Table (1)
   - `sandbox-spa-resources`

9. S3 Bucket (1)
   - For Lambda deployment packages (optional)

**Outputs**:
- SPA Creator API endpoint URL
- Backend API endpoint URL
- DynamoDB table name
- Lambda function names

**Parameters**:
- `EnvironmentName`: Prefix for all resources (default: sandbox)

---

## Scalability & Performance

### API Gateway
- **Throughput**: 10,000 requests per second (default)
- **Burst**: 5,000 requests per second
- **Latency**: ~10-50ms (excluding Lambda execution)
- **Scaling**: Automatic, no configuration needed

### Lambda
- **Concurrency**: 1,000 concurrent executions (default regional limit)
- **Cold Start**: ~1-2 seconds for Python 3.11
- **Warm Execution**: ~100-500ms for SPA creation
- **Scaling**: Automatic, handles spikes instantly

### S3
- **Throughput**: 3,500 PUT/5,500 GET requests per second per prefix
- **Capacity**: Unlimited storage
- **Availability**: 99.99% SLA
- **Durability**: 99.999999999% (11 nines)

### DynamoDB
- **On-Demand Mode**: Auto-scales to handle traffic
- **Throughput**: Unlimited requests per second
- **Latency**: Single-digit milliseconds
- **Availability**: 99.99% SLA

---

## Monitoring & Observability

### CloudWatch Logs

**Log Groups**:
- `/aws/lambda/sandbox-spa-creator`
- `/aws/lambda/sandbox-backend-list-bucket`
- `/aws/lambda/sandbox-backend-upload-url`
- `/aws/lambda/sandbox-backend-user-info`

**Log Retention**: 30 days (default, configurable)

**Log Contents**:
- Lambda execution start/end
- Request/response payloads
- Error stack traces
- Custom application logs

### CloudWatch Metrics

**Lambda Metrics**:
- Invocations
- Duration (p50, p90, p99)
- Errors
- Throttles
- Concurrent executions

**API Gateway Metrics**:
- Request count
- 4xx errors
- 5xx errors
- Latency (integration + total)
- Cache hit/miss (if caching enabled)

**DynamoDB Metrics**:
- Consumed read/write capacity units
- Throttled requests
- System errors

### Alarms (Recommended for Production)

1. **Lambda Errors**: Alert if error rate > 5%
2. **API Gateway 5xx**: Alert if count > 10 in 5 minutes
3. **Lambda Duration**: Alert if p99 > 10 seconds
4. **DynamoDB Throttles**: Alert if any throttling occurs

---

## Disaster Recovery & Business Continuity

### Backup Strategy

**S3 Buckets**:
- Versioning: Disabled (single version only)
- Cross-region replication: Not configured (POC)
- Lifecycle policies: Not configured (manual cleanup)

**DynamoDB Table**:
- Point-in-time recovery: Not enabled (POC)
- On-demand backups: Manual only
- Recovery time: Minutes to hours

**Lambda Functions**:
- Code stored in CloudFormation stack
- Can be redeployed from source in minutes
- No state to recover

### High Availability

**Multi-AZ Deployment**:
- API Gateway: Multi-AZ by default
- Lambda: Multi-AZ by default
- S3: Multi-AZ by default (Standard storage class)
- DynamoDB: Multi-AZ by default

**Failure Scenarios**:
- Single AZ failure: No impact (automatic failover)
- Regional failure: Manual deployment to new region required
- Service disruption: Automatic retries in SDK

---

## Cost Model

### Monthly Cost Breakdown (Example: 1000 SPA creations)

| Service | Usage | Cost |
|---------|-------|------|
| API Gateway | 1,100 requests | $0.00 (Free Tier) |
| Lambda Invocations | 1,100 | $0.00 (Free Tier) |
| Lambda Duration | 1,100 × 2s @ 512MB | $0.00 (Free Tier) |
| S3 Storage | 50GB | $1.15 |
| S3 PUT Requests | 2,200 | $0.01 |
| S3 GET Requests | 10,000 | $0.00 |
| DynamoDB Writes | 1,100 | $1.38 |
| DynamoDB Reads | 500 | $0.13 |
| **Total** | | **~$2.67/month** |

**Free Tier Benefits** (First 12 Months):
- Lambda: 1M requests/month
- API Gateway: 1M requests/month
- S3: 5GB storage, 20,000 GET, 2,000 PUT
- DynamoDB: 25GB storage, 25 WCU, 25 RCU

---

## Limitations & Constraints

### Technical Limitations

1. **S3 Bucket Naming**:
   - Globally unique (conflicts possible)
   - 3-63 characters
   - Lowercase only
   - No special characters except hyphens

2. **Lambda Timeout**:
   - Max 15 minutes
   - SPA Creator set to 5 minutes
   - Backend functions set to 30 seconds

3. **API Gateway Payload**:
   - Max 10MB request/response
   - Not an issue for JSON payloads

4. **DynamoDB Item Size**:
   - Max 400KB per item
   - Not an issue for metadata records

### Architectural Constraints

1. **No Authentication**:
   - POC only - anyone with URL can create SPAs
   - Production requires API keys or OAuth

2. **No User Quotas**:
   - Single user can create unlimited SPAs
   - Production needs rate limiting

3. **No Automatic Cleanup**:
   - Resources persist until manually deleted
   - Production needs lifecycle management

4. **No Multi-Region**:
   - Single region deployment only
   - Production may need global distribution

---

## Production Readiness Enhancements

### Security Hardening

1. **API Authentication**:
   - Add API keys to API Gateway
   - Implement OAuth 2.0 / JWT validation
   - Restrict by IP address (ServiceNow IPs only)

2. **Encryption**:
   - Enable KMS encryption for S3
   - Use customer-managed keys
   - Enable DynamoDB encryption with CMK

3. **Network Isolation**:
   - Deploy Lambda in VPC
   - Use VPC endpoints for AWS services
   - Implement PrivateLink for API Gateway

### Operational Excellence

1. **Monitoring**:
   - Configure CloudWatch Alarms
   - Set up SNS notifications
   - Create CloudWatch Dashboard

2. **Logging**:
   - Enable CloudTrail for audit
   - Configure S3 access logs
   - Enable API Gateway access logs

3. **Backup & Recovery**:
   - Enable DynamoDB point-in-time recovery
   - Implement S3 versioning
   - Configure automated backups

### Performance Optimization

1. **Lambda**:
   - Increase memory if needed
   - Use Provisioned Concurrency for warm starts
   - Optimize code for faster execution

2. **API Gateway**:
   - Enable caching for read operations
   - Implement throttling rules
   - Use regional endpoints for lower latency

3. **DynamoDB**:
   - Add GSIs for alternative query patterns
   - Consider provisioned capacity for predictable workloads
   - Implement DynamoDB Accelerator (DAX) for caching

---

## Technology Stack Summary

| Layer | Technology | Version |
|-------|-----------|---------|
| Infrastructure | AWS CloudFormation | - |
| API Layer | AWS API Gateway HTTP API | v2 |
| Compute | AWS Lambda | Python 3.11 |
| Storage | Amazon S3 | - |
| Database | Amazon DynamoDB | - |
| Monitoring | Amazon CloudWatch | - |
| SDK | boto3 (AWS SDK for Python) | Latest |
| Deployment | AWS CLI | v2 |

---

## References

### AWS Documentation
- [API Gateway HTTP APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)
- [Lambda Python Runtime](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [S3 Static Website Hosting](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html)
- [DynamoDB Core Components](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.CoreComponents.html)
- [S3 Presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)

### Best Practices
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [Serverless Application Lens](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/welcome.html)
- [Security Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/lambda-security.html)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-06 | Initial | Complete architecture documentation |

---

**Document Purpose**: Technical architecture reference for ServiceNow-AWS Integration POC  
**Audience**: Solutions architects, cloud engineers, technical decision makers  
**Classification**: Public (no sensitive information)
