import json
import boto3
import os
from datetime import datetime, timedelta
from collections import defaultdict
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
urls_table = dynamodb.Table(os.environ.get('URLS_TABLE', 'url-shortener-urls-dev'))
stats_table = dynamodb.Table(os.environ.get('STATS_TABLE', 'url-shortener-stats-dev'))


def parse_user_agent(user_agent):
    """User-Agent에서 디바이스 타입 추출"""
    user_agent = user_agent.lower()
    if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
        return 'mobile'
    elif 'tablet' in user_agent or 'ipad' in user_agent:
        return 'tablet'
    else:
        return 'desktop'


def get_click_stats(url_id):
    """특정 URL의 클릭 통계 조회"""
    # stats 테이블에서 해당 urlId로 시작하는 모든 항목 조회
    response = stats_table.scan(
        FilterExpression=Key('statsId').begins_with(f"{url_id}#")
    )
    
    items = response.get('Items', [])
    
    # 페이지네이션 처리
    while 'LastEvaluatedKey' in response:
        response = stats_table.scan(
            FilterExpression=Key('statsId').begins_with(f"{url_id}#"),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response.get('Items', []))
    
    return items


def calculate_stats(click_items):
    """클릭 데이터로 통계 계산"""
    now = datetime.utcnow()
    today = now.date()
    yesterday = today - timedelta(days=1)
    
    # 초기화
    hourly_clicks = defaultdict(int)  # 시간대별 클릭
    daily_clicks = defaultdict(int)   # 일별 클릭
    device_distribution = defaultdict(int)  # 디바이스 분포
    referer_distribution = defaultdict(int)  # 유입 경로
    today_clicks = 0
    yesterday_clicks = 0
    total_clicks = len(click_items)
    
    for item in click_items:
        timestamp_str = item.get('timestamp', '')
        user_agent = item.get('userAgent', 'unknown')
        referer = item.get('referer', 'direct')
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            click_date = timestamp.date()
            click_hour = timestamp.hour
            
            # 시간대별 클릭 (0-23시)
            hourly_clicks[click_hour] += 1
            
            # 일별 클릭
            daily_clicks[click_date.isoformat()] += 1
            
            # 오늘/어제 클릭
            if click_date == today:
                today_clicks += 1
            elif click_date == yesterday:
                yesterday_clicks += 1
                
        except (ValueError, TypeError):
            pass
        
        # 디바이스 분포
        device = parse_user_agent(user_agent)
        device_distribution[device] += 1
        
        # 유입 경로 (referer 도메인 추출)
        if referer and referer != 'direct':
            try:
                from urllib.parse import urlparse
                domain = urlparse(referer).netloc or 'direct'
                referer_distribution[domain] += 1
            except:
                referer_distribution['direct'] += 1
        else:
            referer_distribution['direct'] += 1
    
    # 시간대별 클릭을 리스트로 변환 (0-23시)
    hourly_clicks_list = [{'hour': h, 'clicks': hourly_clicks[h]} for h in range(24)]
    
    # 일별 클릭을 최근 30일로 정리
    daily_clicks_list = sorted(
        [{'date': d, 'clicks': c} for d, c in daily_clicks.items()],
        key=lambda x: x['date'],
        reverse=True
    )[:30]
    
    return {
        'totalClicks': total_clicks,
        'todayClicks': today_clicks,
        'yesterdayClicks': yesterday_clicks,
        'hourlyClicks': hourly_clicks_list,
        'dailyClicks': daily_clicks_list,
        'deviceDistribution': dict(device_distribution),
        'refererDistribution': dict(referer_distribution)
    }


def handler(event, context):
    try:
        # 1. shortCode 추출
        path_params = event.get('pathParameters', {}) or {}
        short_code = path_params.get('shortCode', '')
        
        if not short_code:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'shortCode is required'})
            }
        
        # 2. URL 정보 조회
        url_response = urls_table.get_item(Key={'urlId': short_code})
        url_item = url_response.get('Item')
        
        if not url_item:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'URL not found'})
            }
        
        # 3. 클릭 데이터 조회
        click_items = get_click_stats(short_code)
        
        # 4. 통계 계산
        stats = calculate_stats(click_items)
        
        # urls 테이블의 clickCount(atomic counter)를 정식 totalClicks로 사용
        url_click_count = int(url_item.get('clickCount', 0))
        stats['totalClicks'] = url_click_count
        
        # 5. 응답
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'urlId': short_code,
                'shortUrl': url_item.get('shortUrl', ''),
                'originalUrl': url_item.get('originalUrl', ''),
                'createdAt': url_item.get('createdAt', ''),
                'stats': stats
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }
