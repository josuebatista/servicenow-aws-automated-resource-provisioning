import json
import boto3
import os
import uuid
from datetime import datetime
from botocore.exceptions import ClientError

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

ENVIRONMENT_NAME = os.environ.get('ENVIRONMENT_NAME', 'sandbox')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
BACKEND_API_URL = os.environ.get('BACKEND_API_URL')
AWS_REGION = os.environ['AWS_REGION']

table = dynamodb.Table(DYNAMODB_TABLE)

def lambda_handler(event, context):
    """Main handler for SPA Creator Lambda"""
    
    print(f"Received event: {json.dumps(event)}")
    
    try:
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        username = body.get('username')
        
        if not username:
            return create_response(400, {'error': 'Username is required'})
        
        sanitized_username = sanitize_username(username)
        unique_id = str(uuid.uuid4())[:8]
        bucket_name = f"{ENVIRONMENT_NAME}-spa-{sanitized_username}-{unique_id}"
        
        print(f"Creating SPA for user: {username}, bucket: {bucket_name}")
        
        create_s3_bucket(bucket_name)
        configure_static_website(bucket_name)
        configure_cors(bucket_name)  # ADD CORS CONFIGURATION
        set_bucket_policy(bucket_name)
        website_url = upload_spa_files(bucket_name, username, sanitized_username)
        track_resource(username, bucket_name, website_url)
        
        response_data = {
            'success': True,
            'username': username,
            'bucketName': bucket_name,
            'websiteUrl': website_url,
            'apiEndpoint': BACKEND_API_URL,
            'region': AWS_REGION,
            'createdAt': datetime.utcnow().isoformat(),
            'message': f'SPA created successfully! Visit {website_url} to see your personal dashboard.'
        }
        
        print(f"SPA created successfully: {json.dumps(response_data)}")
        return create_response(200, response_data)
        
    except Exception as e:
        error_message = f"Error creating SPA: {str(e)}"
        print(error_message)
        return create_response(500, {'error': error_message})


def sanitize_username(username):
    import re
    sanitized = re.sub(r'[^a-z0-9-]', '-', username.lower())
    sanitized = re.sub(r'-+', '-', sanitized)
    sanitized = sanitized.strip('-')
    return sanitized[:30]


def create_s3_bucket(bucket_name):
    try:
        if AWS_REGION == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
            )
        
        s3.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={
                'TagSet': [
                    {'Key': 'Environment', 'Value': ENVIRONMENT_NAME},
                    {'Key': 'Purpose', 'Value': 'User SPA'},
                    {'Key': 'ManagedBy', 'Value': 'ServiceNow-AWS-Integration'}
                ]
            }
        )
        
        print(f"S3 bucket created: {bucket_name}")
        return f"s3://{bucket_name}"
        
    except ClientError as e:
        print(f"Error creating S3 bucket: {e}")
        raise


def configure_static_website(bucket_name):
    try:
        s3.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration={
                'IndexDocument': {'Suffix': 'index.html'},
                'ErrorDocument': {'Key': 'error.html'}
            }
        )
        
        s3.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': False,
                'IgnorePublicAcls': False,
                'BlockPublicPolicy': False,
                'RestrictPublicBuckets': False
            }
        )
        
        print(f"Static website hosting configured for: {bucket_name}")
        
    except ClientError as e:
        print(f"Error configuring static website: {e}")
        raise


def configure_cors(bucket_name):
    """Configure CORS to allow browser uploads"""
    try:
        cors_configuration = {
            'CORSRules': [
                {
                    'AllowedOrigins': ['*'],
                    'AllowedMethods': ['GET', 'POST', 'PUT', 'HEAD'],
                    'AllowedHeaders': ['*'],
                    'ExposeHeaders': ['ETag'],
                    'MaxAgeSeconds': 3000
                }
            ]
        }
        
        s3.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration=cors_configuration
        )
        
        print(f"CORS configured for: {bucket_name}")
        
    except ClientError as e:
        print(f"Error configuring CORS: {e}")
        raise


def set_bucket_policy(bucket_name):
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            }
        ]
    }
    
    try:
        s3.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(policy)
        )
        print(f"Bucket policy set for: {bucket_name}")
        
    except ClientError as e:
        print(f"Error setting bucket policy: {e}")
        raise


def upload_spa_files(bucket_name, username, sanitized_username):
    html_content = generate_html(username, sanitized_username, bucket_name)
    
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key='index.html',
            Body=html_content,
            ContentType='text/html',
            CacheControl='no-cache'
        )
        
        error_html = generate_error_html()
        s3.put_object(
            Bucket=bucket_name,
            Key='error.html',
            Body=error_html,
            ContentType='text/html'
        )
        
        print(f"SPA files uploaded to: {bucket_name}")
        
        website_url = f"http://{bucket_name}.s3-website-{AWS_REGION}.amazonaws.com"
        return website_url
        
    except ClientError as e:
        print(f"Error uploading SPA files: {e}")
        raise


def generate_html(username, sanitized_username, bucket_name):
    """Generate enhanced HTML with full interactive features"""
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{username}'s AWS Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header h1 {{ color: #667eea; margin-bottom: 10px; }}
        .header .subtitle {{ color: #666; font-size: 14px; }}
        .info-card, .action-section {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .info-card h2, .action-section h2 {{ color: #667eea; margin-bottom: 15px; font-size: 20px; }}
        .info-item {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }}
        .info-item:last-child {{ border-bottom: none; }}
        .info-label {{ font-weight: 600; color: #555; }}
        .info-value {{
            color: #888;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            word-break: break-all;
        }}
        .button {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
            margin-right: 10px;
            margin-bottom: 10px;
        }}
        .button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(102, 126, 234, 0.4);
        }}
        .button:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }}
        #fileList {{
            margin-top: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            min-height: 100px;
        }}
        .file-item {{
            padding: 12px;
            background: white;
            margin-bottom: 8px;
            border-radius: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-left: 3px solid #667eea;
        }}
        .file-info {{ flex: 1; }}
        .file-name {{ font-weight: 600; color: #333; }}
        .file-meta {{
            font-size: 12px;
            color: #888;
            margin-top: 4px;
        }}
        .status {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-top: 15px;
        }}
        .status.success {{ background: #d4edda; color: #155724; }}
        .status.error {{ background: #f8d7da; color: #721c24; }}
        .status.loading {{ background: #d1ecf1; color: #0c5460; }}
        .upload-area {{
            border: 2px dashed #ccc;
            border-radius: 8px;
            padding: 40px;
            text-align: center;
            background: #f8f9fa;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 15px;
        }}
        .upload-area:hover {{
            border-color: #667eea;
            background: #f0f4ff;
        }}
        .upload-area.dragover {{
            border-color: #667eea;
            background: #e8f0ff;
            transform: scale(1.02);
        }}
        .upload-icon {{ font-size: 48px; margin-bottom: 10px; }}
        #fileInput {{ display: none; }}
        .empty-state {{
            text-align: center;
            padding: 40px;
            color: #888;
        }}
        .footer {{
            text-align: center;
            color: white;
            margin-top: 40px;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>👋 Welcome, {username}!</h1>
            <p class="subtitle">Your Personal AWS Resource Dashboard</p>
        </div>
        
        <div class="info-card">
            <h2>📊 Resource Information</h2>
            <div class="info-item">
                <span class="info-label">Username:</span>
                <span class="info-value">{username}</span>
            </div>
            <div class="info-item">
                <span class="info-label">S3 Bucket:</span>
                <span class="info-value">{bucket_name}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Region:</span>
                <span class="info-value">{AWS_REGION}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Environment:</span>
                <span class="info-value">{ENVIRONMENT_NAME}</span>
            </div>
        </div>
        
        <div class="action-section">
            <h2>📁 Bucket Contents</h2>
            <button class="button" onclick="loadBucketContents()">🔄 Refresh File List</button>
            <div id="fileList">
                <div class="empty-state">Click "Refresh File List" to load files...</div>
            </div>
        </div>
        
        <div class="action-section">
            <h2>⬆️ Upload File</h2>
            <div class="upload-area" id="uploadArea" onclick="document.getElementById('fileInput').click()">
                <div class="upload-icon">📤</div>
                <p style="font-size: 18px; margin-bottom: 10px; font-weight: 600;">Drop a file here or click to upload</p>
                <p style="color: #888; font-size: 14px;">Upload files to your S3 bucket (max 10MB)</p>
            </div>
            <input type="file" id="fileInput" onchange="uploadFile(this.files[0])">
            <div id="uploadStatus"></div>
        </div>
        
        <div class="footer">
            <p>🚀 Powered by ServiceNow-AWS Integration</p>
            <p style="margin-top: 10px; opacity: 0.8;">Created via API Gateway & Lambda</p>
        </div>
    </div>
    
    <script>
        const bucketName = '{bucket_name}';
        const backendAPI = '{BACKEND_API_URL}';
        
        async function loadBucketContents() {{
            const fileList = document.getElementById('fileList');
            fileList.innerHTML = '<div class="status loading">⏳ Loading files...</div>';
            
            try {{
                const response = await fetch(`${{backendAPI}}/bucket-contents?bucket=${{bucketName}}`);
                const data = await response.json();
                
                if (data.files && data.files.length > 0) {{
                    fileList.innerHTML = data.files.map(file => `
                        <div class="file-item">
                            <div class="file-info">
                                <div class="file-name">📄 ${{file.name}}</div>
                                <div class="file-meta">${{formatBytes(file.size)}} • ${{formatDate(file.lastModified)}}</div>
                            </div>
                        </div>
                    `).join('');
                }} else {{
                    fileList.innerHTML = '<div class="empty-state">No files yet. Upload your first file below!</div>';
                }}
            }} catch (error) {{
                console.error('Error loading files:', error);
                fileList.innerHTML = '<div class="status error">❌ Error loading files</div>';
            }}
        }}
        
        async function uploadFile(file) {{
            if (!file) return;
            
            const uploadStatus = document.getElementById('uploadStatus');
            uploadStatus.innerHTML = '<div class="status loading">⏳ Uploading ' + file.name + '...</div>';
            
            try {{
                console.log('Getting presigned POST...');
                const postResponse = await fetch(`${{backendAPI}}/upload-url`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        bucket: bucketName,
                        filename: file.name,
                        contentType: file.type || 'application/octet-stream'
                    }})
                }});
                
                if (!postResponse.ok) {{
                    throw new Error('Failed to get upload URL');
                }}
                
                const postData = await postResponse.json();
                console.log('Got presigned POST, uploading to S3...');
                
                const formData = new FormData();
                Object.keys(postData.fields).forEach(key => {{
                    formData.append(key, postData.fields[key]);
                }});
                formData.append('file', file);
                
                const uploadResponse = await fetch(postData.uploadUrl, {{
                    method: 'POST',
                    body: formData
                }});
                
                if (uploadResponse.ok || uploadResponse.status === 204) {{
                    console.log('Upload successful!');
                    uploadStatus.innerHTML = '<div class="status success">✅ File uploaded successfully!</div>';
                    setTimeout(() => {{
                        loadBucketContents();
                        uploadStatus.innerHTML = '';
                    }}, 1500);
                }} else {{
                    throw new Error('Upload failed: ' + uploadResponse.statusText);
                }}
                
            }} catch (error) {{
                console.error('Upload error:', error);
                uploadStatus.innerHTML = `<div class="status error">❌ ${{error.message}}</div>`;
            }}
        }}
        
        const uploadArea = document.getElementById('uploadArea');
        
        uploadArea.addEventListener('dragover', (e) => {{
            e.preventDefault();
            uploadArea.classList.add('dragover');
        }});
        
        uploadArea.addEventListener('dragleave', () => {{
            uploadArea.classList.remove('dragover');
        }});
        
        uploadArea.addEventListener('drop', (e) => {{
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file) uploadFile(file);
        }});
        
        function formatBytes(bytes) {{
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
        }}
        
        function formatDate(dateString) {{
            const date = new Date(dateString);
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
        }}
        
        window.addEventListener('load', () => {{
            console.log('Dashboard loaded for bucket:', bucketName);
            loadBucketContents();
        }});
    </script>
</body>
</html>'''
    
    return html


def generate_error_html():
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Error - Page Not Found</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
        }
        h1 { font-size: 72px; margin: 0; }
        p { font-size: 24px; margin: 20px 0; }
        a { color: white; text-decoration: underline; }
    </style>
</head>
<body>
    <div>
        <h1>404</h1>
        <p>Page Not Found</p>
        <a href="index.html">← Back to Dashboard</a>
    </div>
</body>
</html>'''


def track_resource(username, bucket_name, website_url):
    try:
        item = {
            'username': username,
            'createdAt': datetime.utcnow().isoformat(),
            'bucketName': bucket_name,
            'websiteUrl': website_url,
            'region': AWS_REGION,
            'environment': ENVIRONMENT_NAME,
            'status': 'active'
        }
        table.put_item(Item=item)
        print(f"Resource tracked in DynamoDB: {username}")
    except Exception as e:
        print(f"Error tracking resource in DynamoDB: {e}")


def create_response(status_code, body):
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
