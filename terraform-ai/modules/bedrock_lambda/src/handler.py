import json
import boto3
import os
from datetime import datetime

bedrock = boto3.client('bedrock-runtime', region_name='ap-northeast-2')
s3 = boto3.client('s3')

S3_BUCKET = os.environ.get('S3_BUCKET', '')
BEDROCK_MODEL = os.environ.get('BEDROCK_MODEL', 'anthropic.claude-3-haiku-20240307-v1:0')


def get_click_data_summary():
    """S3에서 클릭 데이터 요약 가져오기 (또는 DynamoDB에서)"""
    # TODO: 실제 데이터 연동 시 S3/DynamoDB에서 데이터 조회
    # 예시 데이터 반환
    return {
        "total_clicks": 15000,
        "today_clicks": 500,
        "yesterday_clicks": 480,
        "hourly_distribution": {
            "00-06": 120,
            "06-12": 450,
            "12-18": 680,
            "18-24": 350
        },
        "top_sources": {
            "direct": 5000,
            "google.com": 4000,
            "facebook.com": 3000,
            "twitter.com": 2000
        },
        "device_distribution": {
            "desktop": 8000,
            "mobile": 6000,
            "tablet": 1000
        },
        "trending_urls": [
            {"url": "product-launch", "clicks": 1200, "growth": "+45%"},
            {"url": "summer-sale", "clicks": 980, "growth": "+32%"},
            {"url": "newsletter", "clicks": 750, "growth": "+18%"}
        ]
    }


def invoke_bedrock(prompt):
    """Bedrock Claude 모델 호출"""
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
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


def handler(event, context):
    try:
        # 1. 요청 파싱
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        analysis_type = body.get('type', 'general')  # general, hourly, sources, recommendations
        
        # 2. 클릭 데이터 요약 가져오기
        click_data = get_click_data_summary()
        
        # 3. 분석 타입별 프롬프트 생성
        if analysis_type == 'hourly':
            prompt = f"""
다음은 URL 단축 서비스의 시간대별 클릭 데이터입니다:
{json.dumps(click_data['hourly_distribution'], indent=2, ensure_ascii=False)}

마케팅 담당자에게 다음을 분석해주세요:
1. 가장 활발한 시간대와 그 이유 추정
2. 마케팅 캠페인 최적 시간대 추천
3. 시간대별 타겟팅 전략 제안

한국어로 간결하게 답변해주세요.
"""
        elif analysis_type == 'sources':
            prompt = f"""
다음은 URL 단축 서비스의 유입 경로별 클릭 데이터입니다:
{json.dumps(click_data['top_sources'], indent=2, ensure_ascii=False)}

마케팅 담당자에게 다음을 분석해주세요:
1. 가장 효과적인 유입 채널 분석
2. 각 채널별 최적화 전략
3. 투자 대비 효과(ROI) 개선 방안

한국어로 간결하게 답변해주세요.
"""
        elif analysis_type == 'recommendations':
            prompt = f"""
다음은 URL 단축 서비스의 트렌딩 URL 데이터입니다:
{json.dumps(click_data['trending_urls'], indent=2, ensure_ascii=False)}

전체 클릭 현황:
- 오늘: {click_data['today_clicks']}회
- 어제: {click_data['yesterday_clicks']}회
- 전체: {click_data['total_clicks']}회

마케팅 담당자에게 다음을 제안해주세요:
1. 현재 트렌드 분석
2. 다음 주 마케팅 액션 플랜 3가지
3. 주의해야 할 리스크

한국어로 간결하게 답변해주세요.
"""
        else:  # general
            prompt = f"""
다음은 URL 단축 서비스의 종합 클릭 데이터입니다:

전체 현황:
- 총 클릭: {click_data['total_clicks']}회
- 오늘: {click_data['today_clicks']}회
- 어제: {click_data['yesterday_clicks']}회

시간대별: {json.dumps(click_data['hourly_distribution'], ensure_ascii=False)}
유입경로: {json.dumps(click_data['top_sources'], ensure_ascii=False)}
디바이스: {json.dumps(click_data['device_distribution'], ensure_ascii=False)}

마케팅 담당자에게 종합적인 인사이트를 제공해주세요:
1. 현재 성과 요약 (1-2문장)
2. 주요 발견점 3가지
3. 즉시 실행 가능한 액션 아이템 2가지

한국어로 간결하게 답변해주세요.
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
                'data_summary': click_data,
                'ai_insights': ai_response,
                'generated_at': datetime.utcnow().isoformat()
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e)
            })
        }
