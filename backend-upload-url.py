import json
import boto3
import os
from botocore.exceptions import ClientError
from botocore.config import Config

# Configure boto3 with signature version 4
config = Config(signature_version='s3v4')
s3 = boto3.client('s3', config=config)

def lambda_handler(event, context):
    """
    Generate presigned URL for S3 upload
    Body: {"bucket": "bucket-name", "filename": "file.txt", "contentType": "text/plain"}
    """
    
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        bucket_name = body.get('bucket')
        filename = body.get('filename')
        content_type = body.get('contentType', 'application/octet-stream')
        
        if not bucket_name or not filename:
            return create_response(400, {'error': 'Bucket name and filename are required'})
        
        # Verify bucket belongs to our environment (security check)
        environment = os.environ.get('ENVIRONMENT_NAME', 'sandbox')
        if not bucket_name.startswith(f"{environment}-spa-"):
            return create_response(403, {'error': 'Access denied to this bucket'})
        
        # Sanitize filename (remove path traversal attempts)
        filename = filename.split('/')[-1]  # Get only filename, no directories
        
        print(f"Generating presigned URL for: {bucket_name}/{filename}")
        
        # Generate presigned POST instead of PUT for better compatibility
        presigned_post = s3.generate_presigned_post(
            Bucket=bucket_name,
            Key=filename,
            Fields={
                'Content-Type': content_type
            },
            Conditions=[
                {'Content-Type': content_type},
                ['content-length-range', 1, 10485760]  # 1 byte to 10MB
            ],
            ExpiresIn=300  # 5 minutes
        )
        
        result = {
            'success': True,
            'uploadUrl': presigned_post['url'],
            'fields': presigned_post['fields'],
            'bucket': bucket_name,
            'filename': filename,
            'expiresIn': 300,
            'method': 'POST'
        }
        
        print(f"Presigned POST URL generated successfully")
        return create_response(200, result)
        
    except ClientError as e:
        print(f"S3 Error: {e}")
        return create_response(500, {'error': f'S3 error: {e.response["Error"]["Code"]}'})
    except Exception as e:
        print(f"Error: {e}")
        return create_response(500, {'error': str(e)})


def create_response(status_code, body):
    """Create API Gateway response with CORS headers"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        },
        'body': json.dumps(body, default=str)
    }