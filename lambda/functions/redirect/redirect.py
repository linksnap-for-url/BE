import json
import boto3
import os
import uuid
import urllib.request
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
urls_table = dynamodb.Table(os.environ.get('URLS_TABLE', 'url-shortener-urls-dev'))
stats_table = dynamodb.Table(os.environ.get('STATS_TABLE', 'url-shortener-stats-dev'))


def get_country_from_ip(ip):
    """IP 주소로 국가 코드 조회 (무료 API 사용)"""
    try:
        if not ip or ip == 'unknown' or ip.startswith('127.') or ip.startswith('10.'):
            return 'unknown'
        
        # ip-api.com API 
        url = f"http://ip-api.com/json/{ip}?fields=countryCode"
        req = urllib.request.Request(url, headers={'User-Agent': 'LinkSnap/1.0'})
        
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            return data.get('countryCode', 'unknown')
    except Exception:
        return 'unknown'


def get_client_ip(event):
    """클라이언트 IP 주소 추출"""
    headers = event.get('headers', {}) or {}
    
    # API Gateway에서 전달하는 IP 헤더들 확인
    ip = (
        headers.get('x-forwarded-for', '').split(',')[0].strip() or
        headers.get('x-real-ip', '') or
        event.get('requestContext', {}).get('http', {}).get('sourceIp', '') or
        event.get('requestContext', {}).get('identity', {}).get('sourceIp', '') or
        'unknown'
    )
    return ip


def record_click(short_code, event):
    """클릭 통계 기록"""
    headers = event.get('headers', {}) or {}
    
    # 클라이언트 IP에서 국가 조회
    client_ip = get_client_ip(event)
    country = headers.get('cloudfront-viewer-country') or get_country_from_ip(client_ip)
    
    # url 테이블 클릭 카운트 증가 (가장 중요 — 먼저 실행)
    urls_table.update_item(
        Key={'urlId': short_code},
        UpdateExpression='SET clickCount = if_not_exists(clickCount, :zero) + :inc',
        ExpressionAttributeValues={':inc': 1, ':zero': 0}
    )
    
    # stats 테이블에 상세 클릭 로그 저장 (실패해도 리다이렉트는 정상 처리)
    try:
        stats_table.put_item(
            Item={
                'statsId': f"{short_code}#{uuid.uuid4()}",
                'timestamp': datetime.utcnow().isoformat(),
                'userAgent': headers.get('user-agent', 'unknown'),
                'referer': headers.get('referer', 'direct'),
                'country': country,
                'ip': client_ip
            }
        )
    except Exception as e:
        print(f"[WARN] stats 테이블 기록 실패 (shortCode={short_code}): {e}")


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