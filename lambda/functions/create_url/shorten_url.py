import json
import boto3
import hashlib
import time
import os
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('URLS_TABLE', 'url-shortener-urls-dev'))


def get_base_url(event):
    """API Gateway 요청에서 BASE_URL 동적 생성"""
    request_context = event.get('requestContext', {})
    domain = request_context.get('domainName', '')
    stage = request_context.get('stage', '')
    
    if domain and stage:
        return f"https://{domain}/{stage}"
    
    # 로컬 테스트용 fallback
    return os.environ.get('BASE_URL', 'http://localhost')


def generate_url_id(url):
    """URL + 현재시간 해시해서 6자리 코드 생성"""
    unique_string = f"{url}{time.time()}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:6]


def handler(event, context):
    try:
        # 1. 요청 Body 파싱
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        original_url = body.get('url', '')
        
        # 2. URL 검증
        if not original_url:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'url is required'})
            }
        
        if not original_url.startswith(('http://', 'https://')):
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'url must start with http:// or https://'})
            }
        
        # 3. 데이터 생성
        url_id = generate_url_id(original_url)
        now = datetime.utcnow()
        expires_at = now + timedelta(days=30)
        
        # 4. 단축 URL 생성 (API Gateway에서 동적으로 URL 추출)
        base_url = get_base_url(event)
        short_url = f"{base_url}/{url_id}"
        
        # 5. DynamoDB 저장
        table.put_item(
            Item={
                'urlId': url_id,
                'shortUrl': short_url,
                'originalUrl': original_url,
                'createdAt': now.isoformat(),
                'expiresAt': expires_at.isoformat(),
                'clickCount': 0
            }
        )
        
        # 6. 응답 (shortUrl 추가!)
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'urlId': url_id,
                'shortUrl': short_url,  # ← 추가됨!
                'originalUrl': original_url,
                'createdAt': now.isoformat(),
                'expiresAt': expires_at.isoformat()
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }