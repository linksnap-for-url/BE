import json
import boto3
import os
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
urls_table = dynamodb.Table(os.environ.get('URLS_TABLE', 'url-shortener-urls-dev'))
stats_table = dynamodb.Table(os.environ.get('STATS_TABLE', 'url-shortener-stats-dev'))


def record_click(url_id, event):
    """클릭 통계 기록 (stats 테이블 설계에 맞춤)"""
    headers = event.get('headers', {}) or {}
    
    # stats 테이블에 저장
    stats_table.put_item(
        Item={
            'statsId': f"{url_id}#{uuid.uuid4()}",             # PK
            'timestamp': datetime.utcnow().isoformat(),   # 클릭 시간
            'userAgent': headers.get('user-agent', 'unknown'),  # 브라우저 정보
            'referer': headers.get('referer', 'direct'),        # 유입 경로
            'country': headers.get('cloudfront-viewer-country', 'unknown')  # 국가
        }
    )
    
    # url 테이블 클릭 카운트 증가
    urls_table.update_item(
        Key={'urlId': url_id},
        UpdateExpression='SET clickCount = if_not_exists(clickCount, :zero) + :inc',
        ExpressionAttributeValues={':inc': 1, ':zero': 0}
    )


def handler(event, context):
    try:
        # 1. urlId 추출
        path_params = event.get('pathParameters', {}) or {}
        url_id = path_params.get('urlId', '')
        
        if not url_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'urlId is required'})
            }
        
        # 2. DynamoDB에서 원본 URL 조회
        response = urls_table.get_item(Key={'urlId': url_id})
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
        record_click(url_id, event)
        
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