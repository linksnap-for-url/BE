import json
import boto3
import hashlib
import time
import os
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('URLS_TABLE', 'url-shortener-urls-dev'))


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
        expires_at = now + timedelta(days=30)  # 30일 후 만료
        
        # 4. DynamoDB 저장 (테이블 설계에 맞춤)
        table.put_item(
            Item={
                'urlId': url_id,                          # PK
                'originalUrl': original_url,              # 원본 URL
                'createdAt': now.isoformat(),             # 생성 일시 (ISO 8601)
                'expiresAt': expires_at.isoformat(),      # 만료 시간
                'clickCount': 0                           # 총 클릭 수
            }
        )
        
        # 5. 응답
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'urlId': url_id,
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