import json
import boto3
import os
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
table = dynamodb.Table(DYNAMODB_TABLE)

def lambda_handler(event, context):
    """
    Get user information from DynamoDB
    Query parameter: ?username=john.doe
    """
    
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Get username from query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        username = query_params.get('username')
        
        if not username:
            return create_response(400, {'error': 'Username is required'})
        
        print(f"Querying user info for: {username}")
        
        # Query DynamoDB for user's resources
        response = table.query(
            KeyConditionExpression='username = :username',
            ExpressionAttributeValues={
                ':username': username
            },
            ScanIndexForward=False,  # Sort by createdAt descending (newest first)
            Limit=10  # Get last 10 resources
        )
        
        items = response.get('Items', [])
        
        if not items:
            return create_response(404, {'error': 'No resources found for this user'})
        
        result = {
            'success': True,
            'username': username,
            'resourceCount': len(items),
            'resources': items
        }
        
        print(f"Found {len(items)} resources for user")
        return create_response(200, result)
        
    except ClientError as e:
        print(f"DynamoDB Error: {e}")
        return create_response(500, {'error': f'Database error: {e.response["Error"]["Code"]}'})
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