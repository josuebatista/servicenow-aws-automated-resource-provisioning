import json
import boto3
import os
from botocore.exceptions import ClientError

s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    List contents of an S3 bucket
    Query parameter: ?bucket=bucket-name
    """
    
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Get bucket name from query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        bucket_name = query_params.get('bucket')
        
        if not bucket_name:
            return create_response(400, {'error': 'Bucket name is required'})
        
        # Verify bucket belongs to our environment (security check)
        environment = os.environ.get('ENVIRONMENT_NAME', 'sandbox')
        if not bucket_name.startswith(f"{environment}-spa-"):
            return create_response(403, {'error': 'Access denied to this bucket'})
        
        print(f"Listing contents of bucket: {bucket_name}")
        
        # List objects in bucket
        response = s3.list_objects_v2(Bucket=bucket_name)
        
        # Format file list
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                files.append({
                    'name': obj['Key'],
                    'size': obj['Size'],
                    'lastModified': obj['LastModified'].isoformat(),
                    'url': f"https://{bucket_name}.s3.amazonaws.com/{obj['Key']}"
                })
        
        result = {
            'success': True,
            'bucket': bucket_name,
            'fileCount': len(files),
            'files': files
        }
        
        print(f"Found {len(files)} files in bucket")
        return create_response(200, result)
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            return create_response(404, {'error': 'Bucket not found'})
        elif error_code == 'AccessDenied':
            return create_response(403, {'error': 'Access denied'})
        else:
            print(f"S3 Error: {e}")
            return create_response(500, {'error': f'S3 error: {error_code}'})
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
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        },
        'body': json.dumps(body, default=str)
    }