"""
AI 마케팅 인사이트 Lambda 함수
- DynamoDB에서 실시간 통계 수집
- Bedrock(Claude)으로 마케팅 제안 생성
"""

import json
import boto3
import os
from datetime import datetime
from decimal import Decimal

# AWS 클라이언트
bedrock = boto3.client('bedrock-runtime', region_name='ap-northeast-2')
dynamodb = boto3.resource('dynamodb')

# 환경 변수
BEDROCK_MODEL = os.environ.get('BEDROCK_MODEL', 'anthropic.claude-3-haiku-20240307-v1:0')
URLS_TABLE = os.environ.get('URLS_TABLE', 'url-shortener-urls-dev')
STATS_TABLE = os.environ.get('STATS_TABLE', 'url-shortener-stats-dev')


def decimal_to_float(obj):
    """DynamoDB Decimal을 float로 변환"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj


def get_realtime_stats_from_dynamodb():
    """DynamoDB에서 실시간 통계 가져오기"""
    try:
        urls_table = dynamodb.Table(URLS_TABLE)
        stats_table = dynamodb.Table(STATS_TABLE)

        urls_response = urls_table.scan()
        urls = urls_response.get('Items', [])

        stats_response = stats_table.scan()
        stats = stats_response.get('Items', [])

        referer_counts = {}
        device_counts = {}
        country_counts = {}
        hourly_counts = {str(h): 0 for h in range(24)}

        for stat in stats:
            referer = stat.get('referer', 'direct')
            if referer in ['direct', 'unknown', '']:
                referer = 'direct'
            referer_counts[referer] = referer_counts.get(referer, 0) + 1

            ua = stat.get('userAgent', '').lower()
            if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
                device = 'mobile'
            elif 'tablet' in ua or 'ipad' in ua:
                device = 'tablet'
            else:
                device = 'desktop'
            device_counts[device] = device_counts.get(device, 0) + 1

            country = stat.get('country', 'unknown')
            country_counts[country] = country_counts.get(country, 0) + 1

            timestamp = stat.get('timestamp', '')
            if timestamp:
                try:
                    hour = datetime.fromisoformat(timestamp).hour
                    hourly_counts[str(hour)] = hourly_counts.get(str(hour), 0) + 1
                except:
                    pass

        return decimal_to_float({
            'total_urls': len(urls),
            'total_clicks': len(stats),
            'referer_distribution': referer_counts,
            'device_distribution': device_counts,
            'country_distribution': country_counts,
            'hourly_distribution': hourly_counts,
            'top_urls': sorted(urls, key=lambda x: x.get('clickCount', 0), reverse=True)[:5]
        })
    except Exception as e:
        print(f"DynamoDB 데이터 로드 실패: {e}")
        return None


def invoke_bedrock(prompt):
    """Bedrock Claude 모델 호출"""
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    })

    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL,
        body=body,
        contentType='application/json',
        accept='application/json'
    )

    result = json.loads(response['body'].read())
    return result['content'][0]['text']


# ============================================================
# 프롬프트 빌더
# ============================================================

def build_full_prompt(realtime_data):
    """종합 분석 프롬프트"""
    prompt = f"""
당신은 데이터 기반 마케팅 전문가입니다. 다음 URL 단축 서비스의 실시간 데이터를 분석하고 실행 가능한 마케팅 인사이트를 제공해주세요.

## 실시간 서비스 데이터
- 총 URL: {realtime_data.get('total_urls', 0)}개
- 총 클릭: {realtime_data.get('total_clicks', 0)}회
- 시간대별 클릭: {json.dumps(realtime_data.get('hourly_distribution', {}), indent=2)}
- 유입 경로: {json.dumps(realtime_data.get('referer_distribution', {}), indent=2)}
- 디바이스: {json.dumps(realtime_data.get('device_distribution', {}), indent=2)}
- 국가별: {json.dumps(realtime_data.get('country_distribution', {}), indent=2)}

## 인기 URL TOP 5
{json.dumps([{{'url': u.get('originalUrl', '')[:80], 'clicks': u.get('clickCount', 0)}} for u in realtime_data.get('top_urls', [])], indent=2, ensure_ascii=False)}

다음 형식으로 종합 분석 결과를 제공해주세요:

### 1. 현재 성과 요약 (2-3문장)

### 2. 핵심 인사이트 3가지
(데이터에서 발견된 중요한 패턴과 그 의미)

### 3. 디바이스 & 채널 최적화 전략
(디바이스별, 채널별 데이터를 기반으로 한 전략)

### 4. 시간대별 콘텐츠 전략
(시간대별 클릭 패턴을 기반으로 언제 어떤 콘텐츠를 배포할지)

### 5. 타겟 오디언스 분석
(국가별, 디바이스별 데이터를 기반으로 한 타겟 고객 프로필)

### 6. 이번 주 액션 아이템
1. (즉시 실행 - 가장 효과적인 것)
2. (이번 주 내 - 중기 전략)
3. (다음 주 준비 - 장기 전략)

### 7. 주의할 점 & 리스크
(데이터에서 발견된 위험 신호나 개선 필요 사항)

한국어로 실용적이고 구체적으로 답변해주세요. 숫자와 데이터를 근거로 제시해주세요.
"""
    return prompt


def build_traffic_prompt(realtime_data):
    """트래픽 패턴 분석 프롬프트"""
    hourly = realtime_data.get('hourly_distribution', {})

    peak_hour = max(hourly.items(), key=lambda x: x[1]) if hourly else ('12', 0)
    low_hour = min(hourly.items(), key=lambda x: x[1]) if hourly else ('3', 0)

    prompt = f"""
당신은 마케팅 데이터 분석 전문가입니다. 다음 URL 단축 서비스의 트래픽 데이터를 분석해주세요.

## 실시간 트래픽 데이터
- 총 URL: {realtime_data.get('total_urls', 0)}개
- 총 클릭: {realtime_data.get('total_clicks', 0)}회
- 피크 시간대: {peak_hour[0]}시 ({peak_hour[1]}회)
- 최저 시간대: {low_hour[0]}시 ({low_hour[1]}회)

## 시간대별 분포
{json.dumps(hourly, indent=2)}

## 유입 경로
{json.dumps(realtime_data.get('referer_distribution', {}), indent=2)}

## 디바이스 분포
{json.dumps(realtime_data.get('device_distribution', {}), indent=2)}

## 국가별 분포
{json.dumps(realtime_data.get('country_distribution', {}), indent=2)}

다음 형식으로 분석 결과를 제공해주세요:

### 1. 트래픽 패턴 분석
(시간대별 특징, 피크 타임 분석)

### 2. 콘텐츠 업데이트 추천
(어떤 시간대에 어떤 콘텐츠를 업데이트하면 효과적인지)

### 3. 채널별 마케팅 전략
(유입 경로와 디바이스를 고려한 전략)

### 4. 즉시 실행 가능한 액션 아이템 3가지
(구체적이고 실행 가능한 제안)

한국어로 간결하고 실용적으로 답변해주세요.
"""
    return prompt


def build_conversion_prompt(realtime_data):
    """전환율 분석 프롬프트"""
    prompt = f"""
당신은 e-commerce 마케팅 전문가입니다. 다음 URL 단축 서비스의 데이터를 기반으로 전환 최적화 전략을 제안해주세요.

## 실시간 데이터
- 총 URL: {realtime_data.get('total_urls', 0)}개
- 총 클릭: {realtime_data.get('total_clicks', 0)}회
- 디바이스별: {json.dumps(realtime_data.get('device_distribution', {}), indent=2)}
- 유입 채널별: {json.dumps(realtime_data.get('referer_distribution', {}), indent=2)}
- 국가별: {json.dumps(realtime_data.get('country_distribution', {}), indent=2)}

## 인기 URL
{json.dumps([{{'url': u.get('originalUrl', '')[:80], 'clicks': u.get('clickCount', 0)}} for u in realtime_data.get('top_urls', [])], indent=2, ensure_ascii=False)}

다음을 분석해주세요:

### 1. 전환 핵심 요인 분석
(데이터에서 발견된 전환에 영향을 미치는 요소)

### 2. 디바이스별 최적화 전략
(각 디바이스에 맞는 전환 전략)

### 3. 유입 채널 최적화 방안
(각 채널별 전략)

### 4. 타겟 오디언스 제안
(데이터 기반 타겟 고객 프로필)

### 5. 주간 마케팅 플랜
(월~금 각 요일별 추천 액션)

한국어로 실용적으로 답변해주세요.
"""
    return prompt


# ============================================================
# 메인 핸들러
# ============================================================

def handler(event, context):
    try:
        # 1. 요청 파싱
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body) if body else {}

        analysis_type = body.get('type', 'full')

        # 2. DynamoDB에서 실시간 데이터 수집
        realtime_data = get_realtime_stats_from_dynamodb() or {
            'total_urls': 0, 'total_clicks': 0,
            'referer_distribution': {}, 'device_distribution': {},
            'country_distribution': {}, 'hourly_distribution': {}
        }

        # 3. 분석 타입별 프롬프트 생성
        if analysis_type == 'traffic':
            prompt = build_traffic_prompt(realtime_data)
        elif analysis_type == 'conversion':
            prompt = build_conversion_prompt(realtime_data)
        else:  # full
            prompt = build_full_prompt(realtime_data)

        # 4. Bedrock 호출
        ai_response = invoke_bedrock(prompt)

        # 5. 응답 반환
        response_body = {
            'analysis_type': analysis_type,
            'data_summary': {
                'total_urls': realtime_data.get('total_urls', 0),
                'total_clicks': realtime_data.get('total_clicks', 0),
                'top_referers': list(realtime_data.get('referer_distribution', {}).keys())[:5],
                'top_devices': list(realtime_data.get('device_distribution', {}).keys()),
                'countries': list(realtime_data.get('country_distribution', {}).keys())[:10],
            },
            'model_info': {
                'loaded': False,
                'type': 'bedrock-claude',
                'accuracy': None,
                'auc_roc': None,
                'trained_at': None,
            },
            'conversion_prediction': None,
            'rfm_summary': None,
            'segmentation_summary': None,
            'product_summary': None,
            'ai_insights': ai_response,
            'generated_at': datetime.utcnow().isoformat(),
            'data_source': 'realtime'
        }

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_body, ensure_ascii=False)
        }

    except Exception as e:
        import traceback
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'traceback': traceback.format_exc()
            })
        }
