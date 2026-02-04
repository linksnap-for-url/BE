import json
import boto3
import os
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource('dynamodb')
urls_table = dynamodb.Table(os.environ.get('URLS_TABLE', 'url-shortener-urls-dev'))
stats_table = dynamodb.Table(os.environ.get('STATS_TABLE', 'url-shortener-stats-dev'))


def get_all_urls():
    """모든 URL 조회"""
    response = urls_table.scan()
    items = response.get('Items', [])
    
    while 'LastEvaluatedKey' in response:
        response = urls_table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response.get('Items', []))
    
    return items


def get_all_clicks():
    """모든 클릭 데이터 조회"""
    response = stats_table.scan()
    items = response.get('Items', [])
    
    while 'LastEvaluatedKey' in response:
        response = stats_table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response.get('Items', []))
    
    return items


def handler(event, context):
    try:
        # 1. 모든 URL 조회
        all_urls = get_all_urls()
        total_urls = len(all_urls)
        
        # 2. 인기 URL (클릭수 기준 상위 10개)
        popular_urls = sorted(
            all_urls,
            key=lambda x: int(x.get('clickCount', 0)),
            reverse=True
        )[:10]
        
        popular_urls_list = [
            {
                'urlId': url.get('urlId'),
                'shortUrl': url.get('shortUrl'),
                'originalUrl': url.get('originalUrl'),
                'clickCount': int(url.get('clickCount', 0)),
                'createdAt': url.get('createdAt')
            }
            for url in popular_urls
        ]
        
        # 3. 전체 클릭 통계
        all_clicks = get_all_clicks()
        total_clicks = len(all_clicks)
        
        # 4. 오늘/어제 클릭 수
        now = datetime.utcnow()
        today = now.date()
        yesterday = today - timedelta(days=1)
        
        today_clicks = 0
        yesterday_clicks = 0
        
        for click in all_clicks:
            timestamp_str = click.get('timestamp', '')
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                click_date = timestamp.date()
                
                if click_date == today:
                    today_clicks += 1
                elif click_date == yesterday:
                    yesterday_clicks += 1
            except (ValueError, TypeError):
                pass
        
        # 5. 최근 등록된 URL (최근 10개)
        recent_urls = sorted(
            all_urls,
            key=lambda x: x.get('createdAt', ''),
            reverse=True
        )[:10]
        
        recent_urls_list = [
            {
                'urlId': url.get('urlId'),
                'shortUrl': url.get('shortUrl'),
                'originalUrl': url.get('originalUrl'),
                'clickCount': int(url.get('clickCount', 0)),
                'createdAt': url.get('createdAt')
            }
            for url in recent_urls
        ]
        
        # 6. 응답
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'totalUrls': total_urls,
                'totalClicks': total_clicks,
                'todayClicks': today_clicks,
                'yesterdayClicks': yesterday_clicks,
                'popularUrls': popular_urls_list,
                'recentUrls': recent_urls_list
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
