import json
import boto3
import os
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
urls_table = dynamodb.Table(os.environ.get('URLS_TABLE', 'url-shortener-urls-dev'))
stats_table = dynamodb.Table(os.environ.get('STATS_TABLE', 'url-shortener-stats-dev'))


def record_click(short_code, event):
    """클릭 통계 기록"""
    headers = event.get('headers', {}) or {}
    
    # stats 테이블에 저장
    stats_table.put_item(
        Item={
            'statsId': f"{short_code}#{uuid.uuid4()}",
            'timestamp': datetime.utcnow().isoformat(),
            'userAgent': headers.get('user-agent', 'unknown'),
            'referer': headers.get('referer', 'direct'),
            'country': headers.get('cloudfront-viewer-country', 'unknown')
        }
    )
    
    # url 테이블 클릭 카운트 증가
    urls_table.update_item(
        Key={'urlId': short_code},
        UpdateExpression='SET clickCount = if_not_exists(clickCount, :zero) + :inc',
        ExpressionAttributeValues={':inc': 1, ':zero': 0}
    )


def handler(event, context):
    try:
        # 1. shortCode 추출 (API Gateway 라우트: GET /{shortCode})
        path_params = event.get('pathParameters', {}) or {}
        short_code = path_params.get('shortCode', '')
        
        if not short_code:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'shortCode is required'})
            }
        
        # 2. DynamoDB에서 원본 URL 조회 (urlId = shortCode)
        response = urls_table.get_item(Key={'urlId': short_code})
        item = response.get('Item')
        
        if not item:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'URL not found'})
            }
        
        # 3. 만료 체크
        expires_at = item.get('expiresAt', '')
        if expires_at:
            if datetime.utcnow().isoformat() > expires_at:
                return {
                    'statusCode': 410,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'URL has expired'})
                }
        
        # 4. 통계 기록
        record_click(short_code, event)
        
        # 5. 리다이렉트
        return {
            'statusCode': 301,
            'headers': {
                'Location': item['originalUrl'],
                'Cache-Control': 'no-cache'
            },
            'body': ''
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }