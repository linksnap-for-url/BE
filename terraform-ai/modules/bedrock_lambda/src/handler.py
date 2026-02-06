"""
AI 마케팅 인사이트 Lambda 함수
- S3에서 분석 데이터 로드
- SageMaker Endpoint로 예측 (선택)
- Bedrock(Claude)으로 마케팅 제안 생성
"""

import json
import boto3
import os
from datetime import datetime
from decimal import Decimal

# AWS 클라이언트
bedrock = boto3.client('bedrock-runtime', region_name='ap-northeast-2')
s3 = boto3.client('s3')
sagemaker = boto3.client('sagemaker-runtime', region_name='ap-northeast-2')
dynamodb = boto3.resource('dynamodb')

# 환경 변수
S3_BUCKET = os.environ.get('S3_BUCKET', '')
BEDROCK_MODEL = os.environ.get('BEDROCK_MODEL', 'anthropic.claude-3-haiku-20240307-v1:0')
SAGEMAKER_ENDPOINT = os.environ.get('SAGEMAKER_ENDPOINT', '')
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


def get_traffic_data_from_s3():
    """S3에서 트래픽 데이터 요약 가져오기"""
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key='processed-data/summary.json')
        return json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"S3 데이터 로드 실패: {e}")
        return None


def get_realtime_stats_from_dynamodb():
    """DynamoDB에서 실시간 통계 가져오기"""
    try:
        urls_table = dynamodb.Table(URLS_TABLE)
        stats_table = dynamodb.Table(STATS_TABLE)
        
        # 모든 URL 조회
        urls_response = urls_table.scan()
        urls = urls_response.get('Items', [])
        
        # 클릭 통계 조회
        stats_response = stats_table.scan()
        stats = stats_response.get('Items', [])
        
        # 유입 경로 집계
        referer_counts = {}
        device_counts = {}
        hourly_counts = {str(h): 0 for h in range(24)}
        
        for stat in stats:
            # Referer 집계
            referer = stat.get('referer', 'direct')
            if referer in ['direct', 'unknown', '']:
                referer = 'direct'
            referer_counts[referer] = referer_counts.get(referer, 0) + 1
            
            # User-Agent에서 디바이스 추출
            ua = stat.get('userAgent', '').lower()
            if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
                device = 'mobile'
            elif 'tablet' in ua or 'ipad' in ua:
                device = 'tablet'
            else:
                device = 'desktop'
            device_counts[device] = device_counts.get(device, 0) + 1
            
            # 시간대 집계
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
            'hourly_distribution': hourly_counts,
            'top_urls': sorted(urls, key=lambda x: x.get('clickCount', 0), reverse=True)[:5]
        })
    except Exception as e:
        print(f"DynamoDB 데이터 로드 실패: {e}")
        return None


def invoke_sagemaker(features):
    """SageMaker Endpoint로 예측"""
    if not SAGEMAKER_ENDPOINT:
        return None
    
    try:
        # CSV 형식으로 변환
        payload = ','.join(map(str, features))
        
        response = sagemaker.invoke_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT,
            ContentType='text/csv',
            Body=payload
        )
        
        result = response['Body'].read().decode('utf-8')
        return float(result)
    except Exception as e:
        print(f"SageMaker 호출 실패: {e}")
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


def analyze_traffic_patterns(data):
    """트래픽 패턴 분석 프롬프트 생성"""
    hourly = data.get('hourly_distribution', {})
    
    # 피크 시간대 찾기
    peak_hour = max(hourly.items(), key=lambda x: x[1]) if hourly else ('12', 0)
    low_hour = min(hourly.items(), key=lambda x: x[1]) if hourly else ('3', 0)
    
    prompt = f"""
당신은 마케팅 데이터 분석 전문가입니다. 다음 URL 단축 서비스의 트래픽 데이터를 분석해주세요.

## 트래픽 데이터
- 총 URL: {data.get('total_urls', 0)}개
- 총 클릭: {data.get('total_clicks', 0)}회
- 피크 시간대: {peak_hour[0]}시 ({peak_hour[1]}회)
- 최저 시간대: {low_hour[0]}시 ({low_hour[1]}회)

## 시간대별 분포
{json.dumps(hourly, indent=2)}

## 유입 경로
{json.dumps(data.get('referer_distribution', {}), indent=2)}

## 디바이스 분포
{json.dumps(data.get('device_distribution', {}), indent=2)}

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


def analyze_conversion(data, conversion_prob=None):
    """전환율 분석 및 마케팅 제안"""
    prompt = f"""
당신은 e-commerce 마케팅 전문가입니다. 다음 데이터를 기반으로 마케팅 제안을 해주세요.

## 현재 상황
- 총 클릭: {data.get('total_clicks', 0)}회
- 인기 URL 수: {len(data.get('top_urls', []))}개

## 인기 콘텐츠 (클릭수 기준)
{json.dumps([{'url': u.get('originalUrl', '')[:50], 'clicks': u.get('clickCount', 0)} for u in data.get('top_urls', [])], indent=2, ensure_ascii=False)}

## 유입 경로 분석
{json.dumps(data.get('referer_distribution', {}), indent=2)}

{"## AI 예측 전환 확률: " + str(round(conversion_prob * 100, 1)) + "%" if conversion_prob else ""}

다음을 분석해주세요:

### 1. 트렌딩 콘텐츠 분석
(어떤 콘텐츠가 인기 있고, 왜 인기 있는지)

### 2. 유입 채널 최적화 방안
(각 채널별 강점과 개선점)

### 3. 타겟 오디언스 제안
(데이터 기반 타겟 고객 프로필)

### 4. 주간 마케팅 플랜
(월~금 각 요일별 추천 액션)

한국어로 실용적으로 답변해주세요.
"""
    return prompt


def handler(event, context):
    try:
        # 1. 요청 파싱
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body) if body else {}
        
        analysis_type = body.get('type', 'full')  # full, traffic, conversion, realtime
        
        # 2. 데이터 수집
        s3_data = get_traffic_data_from_s3()
        realtime_data = get_realtime_stats_from_dynamodb()
        
        # 사용할 데이터 선택
        data = realtime_data or s3_data or {
            'total_urls': 0,
            'total_clicks': 0,
            'referer_distribution': {},
            'device_distribution': {},
            'hourly_distribution': {}
        }
        
        # 3. 분석 타입별 처리
        if analysis_type == 'traffic':
            prompt = analyze_traffic_patterns(data)
        elif analysis_type == 'conversion':
            # SageMaker로 전환 예측 (endpoint가 있으면)
            conversion_prob = None
            if SAGEMAKER_ENDPOINT:
                # 예시 특성: [total_events, page_views, added_to_cart, duration, hour, dow, device, source]
                features = [10, 5, 1, 15.0, 14, 2, 1, 1]
                conversion_prob = invoke_sagemaker(features)
            prompt = analyze_conversion(data, conversion_prob)
        else:  # full
            prompt = f"""
당신은 마케팅 데이터 분석 전문가입니다. 다음 URL 단축 서비스의 종합 데이터를 분석하고 마케팅 인사이트를 제공해주세요.

## 1. 종합 데이터
- 총 URL: {data.get('total_urls', 0)}개
- 총 클릭: {data.get('total_clicks', 0)}회

## 2. 시간대별 트래픽
{json.dumps(data.get('hourly_distribution', {}), indent=2)}

## 3. 유입 경로
{json.dumps(data.get('referer_distribution', {}), indent=2)}

## 4. 디바이스 분포
{json.dumps(data.get('device_distribution', {}), indent=2)}

## 5. 인기 URL
{json.dumps([{'url': u.get('originalUrl', '')[:50] if isinstance(u, dict) else '', 'clicks': u.get('clickCount', 0) if isinstance(u, dict) else 0} for u in data.get('top_urls', [])[:3]], indent=2, ensure_ascii=False)}

다음 형식으로 종합 분석 결과를 제공해주세요:

### 1. 현재 성과 요약 (2-3문장)

### 2. 핵심 인사이트 3가지

### 3. 콘텐츠 업데이트 최적 시간대
(언제 어떤 콘텐츠를 업데이트하면 효과적인지)

### 4. 채널별 전략
(유입 경로와 디바이스별 차별화 전략)

### 5. 이번 주 액션 아이템
1. (즉시 실행)
2. (이번 주 내)
3. (다음 주 준비)

### 6. 주의할 점
(데이터에서 발견된 리스크나 개선 필요 사항)

한국어로 실용적이고 구체적으로 답변해주세요.
"""
        
        # 4. Bedrock 호출
        ai_response = invoke_bedrock(prompt)
        
        # 5. 응답 반환
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'analysis_type': analysis_type,
                'data_summary': {
                    'total_urls': data.get('total_urls', 0),
                    'total_clicks': data.get('total_clicks', 0),
                    'top_referers': list(data.get('referer_distribution', {}).keys())[:5],
                    'top_devices': list(data.get('device_distribution', {}).keys())
                },
                'ai_insights': ai_response,
                'generated_at': datetime.utcnow().isoformat(),
                'data_source': 'realtime' if realtime_data else 's3'
            }, ensure_ascii=False)
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
