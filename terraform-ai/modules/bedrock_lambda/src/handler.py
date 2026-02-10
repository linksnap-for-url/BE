"""
AI 마케팅 인사이트 Lambda 함수
- S3에서 학습된 XGBoost 모델 로드 (pickle)
- S3에서 K-Means 세그멘테이션 + RFM + 상품 인사이트 로드
- DynamoDB에서 실시간 통계 수집
- 모델로 전환 예측 수행
- Bedrock(Claude)으로 마케팅 제안 생성
"""

import json
import boto3
import os
import pickle
import tempfile
from datetime import datetime
from decimal import Decimal

# AWS 클라이언트
bedrock = boto3.client('bedrock-runtime', region_name='ap-northeast-2')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# 환경 변수
S3_BUCKET = os.environ.get('S3_BUCKET', '')
BEDROCK_MODEL = os.environ.get('BEDROCK_MODEL', 'anthropic.claude-3-haiku-20240307-v1:0')
URLS_TABLE = os.environ.get('URLS_TABLE', 'url-shortener-urls-dev')
STATS_TABLE = os.environ.get('STATS_TABLE', 'url-shortener-stats-dev')

# 모델 캐시 (Lambda warm start 활용)
_model_cache = None
_metadata_cache = None
_insights_cache = None


def decimal_to_float(obj):
    """DynamoDB Decimal을 float로 변환"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj


def load_model_from_s3():
    """S3에서 XGBoost 모델 로드 (캐싱)"""
    global _model_cache, _metadata_cache

    if _model_cache is not None:
        print("모델 캐시 사용")
        return _model_cache, _metadata_cache

    try:
        # 모델 파일 다운로드
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp:
            s3.download_file(S3_BUCKET, 'model/model.pkl', tmp.name)
            with open(tmp.name, 'rb') as f:
                _model_cache = pickle.load(f)
            os.unlink(tmp.name)

        # 메타데이터 로드
        response = s3.get_object(Bucket=S3_BUCKET, Key='model/metadata.json')
        _metadata_cache = json.loads(response['Body'].read().decode('utf-8'))

        print(f"모델 로드 완료: {_metadata_cache.get('trained_at', 'unknown')}")
        return _model_cache, _metadata_cache

    except Exception as e:
        print(f"모델 로드 실패: {e}")
        return None, None


def load_insights_from_s3():
    """S3에서 종합 인사이트 데이터 로드 (캐싱)"""
    global _insights_cache

    if _insights_cache is not None:
        print("인사이트 캐시 사용")
        return _insights_cache

    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key='processed-data/insights.json')
        _insights_cache = json.loads(response['Body'].read().decode('utf-8'))
        print("인사이트 로드 완료")
        return _insights_cache
    except Exception as e:
        print(f"인사이트 데이터 로드 실패: {e}")
        return None


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


def predict_conversion(model, metadata, session_data):
    """XGBoost 모델로 전환 확률 예측"""
    if model is None or metadata is None:
        return None

    try:
        feature_cols = metadata.get('feature_columns', [])

        # 기본값 설정
        defaults = {
            'total_events': 10,
            'page_views': 5,
            'add_to_cart': 1,
            'unique_products': 3,
            'session_duration_min': 15.0,
            'hour': datetime.utcnow().hour,
            'day_of_week': datetime.utcnow().weekday(),
            'is_weekend': 1 if datetime.utcnow().weekday() >= 5 else 0,
            'device_encoded': session_data.get('device_encoded', 1),
            'source_encoded': session_data.get('source_encoded', 0),
            'age': session_data.get('age', 30),
            'marketing_opt_in': session_data.get('marketing_opt_in', 1),
        }

        # session_data로 오버라이드
        for key in session_data:
            if key in defaults:
                defaults[key] = session_data[key]

        # 피처 배열 생성
        features = [[defaults.get(col, 0) for col in feature_cols]]

        # 예측
        prob = model.predict_proba(features)[0][1]
        return float(prob)

    except Exception as e:
        print(f"예측 실패: {e}")
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

def build_full_prompt(realtime_data, insights_data, conversion_prob):
    """종합 분석 프롬프트 (XGBoost + RFM + K-Means + 상품 + 실시간)"""
    model_perf = insights_data.get('model_performance', {}) if insights_data else {}
    data_summary = insights_data.get('data_summary', {}) if insights_data else {}
    device_analysis = insights_data.get('device_analysis', {}) if insights_data else {}
    source_analysis = insights_data.get('source_analysis', {}) if insights_data else {}
    hourly_conv = insights_data.get('hourly_conversion', {}) if insights_data else {}
    rfm = insights_data.get('rfm_analysis', {}) if insights_data else {}
    segmentation = insights_data.get('customer_segmentation', {}) if insights_data else {}
    product = insights_data.get('product_analysis', {}) if insights_data else {}

    # RFM 세그먼트 요약
    rfm_summary = ""
    if rfm and rfm.get('segments'):
        rfm_summary = "\n## RFM 고객 가치 분석\n"
        rfm_summary += f"- 총 고객: {rfm.get('summary', {}).get('total_customers', 'N/A')}명\n"
        rfm_summary += f"- 평균 구매 빈도: {rfm.get('summary', {}).get('avg_frequency', 'N/A')}회\n"
        rfm_summary += f"- 평균 구매 금액: ${rfm.get('summary', {}).get('avg_monetary', 'N/A')}\n\n"
        rfm_summary += "| 세그먼트 | 고객 수 | 비율 | 평균 주문 | 평균 지출 |\n"
        rfm_summary += "|----------|---------|------|-----------|----------|\n"
        for seg_name, seg_data in rfm['segments'].items():
            rfm_summary += f"| {seg_name} | {seg_data['count']} | {seg_data['percentage']}% | {seg_data['avg_orders']} | ${seg_data['avg_spending_usd']:.0f} |\n"

    # K-Means 세그먼트 요약
    kmeans_summary = ""
    if segmentation and segmentation.get('clusters'):
        kmeans_summary = "\n## K-Means 행동 기반 세그멘테이션\n"
        for cluster_name, cluster_data in segmentation['clusters'].items():
            kmeans_summary += f"\n### {cluster_name} ({cluster_data['count']}명, {cluster_data['percentage']}%)\n"
            kmeans_summary += f"- 평균 나이: {cluster_data['avg_age']}세 | 주문: {cluster_data['avg_orders']}회 | 지출: ${cluster_data['avg_spending_usd']:.0f}\n"
            kmeans_summary += f"- 세션: {cluster_data['avg_sessions']}회 | 페이지뷰: {cluster_data['avg_page_views']}회 | 장바구니: {cluster_data['avg_cart_adds']}회\n"
            kmeans_summary += f"- 마케팅 수신 동의율: {cluster_data['marketing_opt_in_rate']:.1%}\n"
            if cluster_data.get('preferred_devices'):
                kmeans_summary += f"- 선호 디바이스: {json.dumps(cluster_data['preferred_devices'])}\n"
            if cluster_data.get('preferred_sources'):
                kmeans_summary += f"- 선호 채널: {json.dumps(cluster_data['preferred_sources'])}\n"

    # 상품 분석 요약
    product_summary = ""
    if product and product.get('categories'):
        product_summary = "\n## 상품 카테고리 분석\n"
        product_summary += f"- 총 상품: {product.get('summary', {}).get('total_products', 'N/A')}개\n"
        product_summary += f"- 총 매출: ${product.get('summary', {}).get('total_revenue', 0):,.0f}\n\n"
        product_summary += "| 카테고리 | 판매량 | 매출 | 고유 고객 | 평균 평점 |\n"
        product_summary += "|----------|--------|------|-----------|----------|\n"
        for cat_name, cat_data in product['categories'].items():
            product_summary += f"| {cat_name} | {cat_data['total_sold']:,} | ${cat_data['total_revenue_usd']:,.0f} | {cat_data['unique_customers']:,} | {cat_data['avg_rating']:.1f} |\n"

    prompt = f"""
당신은 데이터 기반 마케팅 전문가입니다. 다음 URL 단축 서비스의 데이터를 종합 분석하고 실행 가능한 마케팅 인사이트를 제공해주세요.

## 1. 실시간 서비스 데이터
- 총 URL: {realtime_data.get('total_urls', 0)}개
- 총 클릭: {realtime_data.get('total_clicks', 0)}회
- 시간대별 클릭: {json.dumps(realtime_data.get('hourly_distribution', {}), indent=2)}
- 유입 경로: {json.dumps(realtime_data.get('referer_distribution', {}), indent=2)}
- 디바이스: {json.dumps(realtime_data.get('device_distribution', {}), indent=2)}
- 국가별: {json.dumps(realtime_data.get('country_distribution', {}), indent=2)}

## 2. AI 모델 분석 결과 (XGBoost 전환 예측 모델)
- 모델 정확도: {model_perf.get('accuracy', 'N/A')}
- AUC-ROC: {model_perf.get('auc_roc', 'N/A')}
- 주요 전환 요인: {json.dumps(model_perf.get('feature_importance', {}), indent=2)}

## 3. e-commerce 데이터 인사이트 (세션 분석)
- 전체 전환율: {data_summary.get('conversion_rate', 'N/A')}
- 평균 페이지뷰: {data_summary.get('avg_page_views', 'N/A')}
- 평균 세션 시간: {data_summary.get('avg_session_duration_min', 'N/A')}분

## 4. 디바이스별 전환율
{json.dumps(device_analysis, indent=2)}

## 5. 유입 채널별 전환율
{json.dumps(source_analysis, indent=2)}

## 6. 시간대별 전환율 (0~23시)
{json.dumps(hourly_conv, indent=2)}

{f"## 7. 현재 세션 전환 예측 확률: {conversion_prob:.1%}" if conversion_prob else ""}

{rfm_summary}

{kmeans_summary}

{product_summary}

다음 형식으로 종합 분석 결과를 제공해주세요:

### 1. 현재 성과 요약 (2-3문장)

### 2. AI 모델 기반 핵심 인사이트 3가지
(XGBoost 모델이 발견한 전환에 가장 큰 영향을 미치는 요소와 그 의미)

### 3. 고객 세그먼트별 전략
(RFM 분석과 K-Means 세그멘테이션 결과를 기반으로 각 세그먼트에 맞는 마케팅 전략)

### 4. 상품 & 카테고리 전략
(매출, 평점, 디바이스/채널별 데이터를 기반으로 한 상품 추천 전략)

### 5. 디바이스 & 채널 최적화 전략
(데이터에서 발견된 디바이스별, 채널별 전환율 차이를 기반으로)

### 6. 시간대별 콘텐츠 전략
(시간대별 전환율을 기반으로 언제 어떤 콘텐츠를 배포할지)

### 7. 이번 주 액션 아이템
1. (즉시 실행 - 가장 효과적인 것)
2. (이번 주 내 - 중기 전략)
3. (다음 주 준비 - 장기 전략)

### 8. 주의할 점 & 리스크
(데이터에서 발견된 위험 신호나 개선 필요 사항)

한국어로 실용적이고 구체적으로 답변해주세요. 숫자와 데이터를 근거로 제시해주세요.
"""
    return prompt


def build_traffic_prompt(realtime_data, insights_data):
    """트래픽 패턴 분석 프롬프트"""
    hourly = realtime_data.get('hourly_distribution', {})
    hourly_conv = insights_data.get('hourly_conversion', {}) if insights_data else {}
    daily_conv = insights_data.get('daily_conversion', {}) if insights_data else {}

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

## 시간대별 전환율 (AI 모델 분석)
{json.dumps(hourly_conv, indent=2)}

## 요일별 전환율
{json.dumps(daily_conv, indent=2)}

## 유입 경로
{json.dumps(realtime_data.get('referer_distribution', {}), indent=2)}

## 디바이스 분포
{json.dumps(realtime_data.get('device_distribution', {}), indent=2)}

## 국가별 분포
{json.dumps(realtime_data.get('country_distribution', {}), indent=2)}

다음 형식으로 분석 결과를 제공해주세요:

### 1. 트래픽 패턴 분석
(시간대별 특징, 피크 타임 분석, 요일별 특징)

### 2. 콘텐츠 업데이트 추천
(어떤 시간대에 어떤 콘텐츠를 업데이트하면 효과적인지)

### 3. 채널별 마케팅 전략
(유입 경로와 디바이스를 고려한 전략)

### 4. 즉시 실행 가능한 액션 아이템 3가지
(구체적이고 실행 가능한 제안)

한국어로 간결하고 실용적으로 답변해주세요.
"""
    return prompt


def build_conversion_prompt(realtime_data, insights_data, conversion_prob):
    """전환율 분석 프롬프트 (RFM + 세그멘테이션 포함)"""
    device_analysis = insights_data.get('device_analysis', {}) if insights_data else {}
    source_analysis = insights_data.get('source_analysis', {}) if insights_data else {}
    model_perf = insights_data.get('model_performance', {}) if insights_data else {}
    rfm = insights_data.get('rfm_analysis', {}) if insights_data else {}
    segmentation = insights_data.get('customer_segmentation', {}) if insights_data else {}

    # RFM 세그먼트 텍스트
    rfm_text = ""
    if rfm and rfm.get('segments'):
        rfm_text = "\n## RFM 고객 가치 분석\n"
        for seg_name, seg_data in rfm['segments'].items():
            rfm_text += f"- {seg_name}: {seg_data['count']}명 ({seg_data['percentage']}%) | 평균 주문 {seg_data['avg_orders']}회 | 평균 지출 ${seg_data['avg_spending_usd']:.0f}\n"

    # K-Means 세그먼트 텍스트
    kmeans_text = ""
    if segmentation and segmentation.get('clusters'):
        kmeans_text = "\n## K-Means 행동 세그먼트\n"
        for cluster_name, cluster_data in segmentation['clusters'].items():
            kmeans_text += f"- {cluster_name}: {cluster_data['count']}명 ({cluster_data['percentage']}%) | 세션 {cluster_data['avg_sessions']}회 | 전환 {cluster_data['avg_orders']}회 | 지출 ${cluster_data['avg_spending_usd']:.0f}\n"

    prompt = f"""
당신은 e-commerce 마케팅 전문가입니다. AI 모델 분석 결과를 기반으로 마케팅 제안을 해주세요.

## AI 전환 예측 모델 성능
- 정확도: {model_perf.get('accuracy', 'N/A')}
- AUC-ROC: {model_perf.get('auc_roc', 'N/A')}
- 주요 전환 요인: {json.dumps(model_perf.get('feature_importance', {}), indent=2)}

## 디바이스별 전환율
{json.dumps(device_analysis, indent=2)}

## 유입 채널별 전환율
{json.dumps(source_analysis, indent=2)}

## 현재 실시간 데이터
- 총 클릭: {realtime_data.get('total_clicks', 0)}회
- 인기 URL: {json.dumps([{{'url': u.get('originalUrl', '')[:50], 'clicks': u.get('clickCount', 0)}} for u in realtime_data.get('top_urls', [])], indent=2, ensure_ascii=False)}

{f"## AI 예측 전환 확률: {conversion_prob:.1%}" if conversion_prob else ""}

{rfm_text}

{kmeans_text}

다음을 분석해주세요:

### 1. 전환 핵심 요인 분석
(AI 모델이 발견한 전환에 가장 큰 영향을 미치는 요소)

### 2. 고객 세그먼트별 전환 전략
(RFM 분석과 K-Means 세그먼트를 기반으로 각 그룹에 맞는 전환 전략)

### 3. 디바이스별 최적화 전략
(전환율 차이를 기반으로 각 디바이스에 맞는 전략)

### 4. 유입 채널 최적화 방안
(각 채널별 전환율 차이를 활용한 전략)

### 5. 타겟 오디언스 제안
(데이터 기반 타겟 고객 프로필 - 어떤 세그먼트에 집중해야 하는지)

### 6. 주간 마케팅 플랜
(월~금 각 요일별 추천 액션)

한국어로 실용적으로 답변해주세요.
"""
    return prompt


def build_segmentation_prompt(realtime_data, insights_data):
    """고객 세그멘테이션 전용 분석 프롬프트"""
    rfm = insights_data.get('rfm_analysis', {}) if insights_data else {}
    segmentation = insights_data.get('customer_segmentation', {}) if insights_data else {}
    product = insights_data.get('product_analysis', {}) if insights_data else {}

    prompt = f"""
당신은 CRM 및 고객 세그멘테이션 전문가입니다. 다음 데이터를 분석하고 각 고객 그룹에 맞는 전략을 제안해주세요.

## RFM 고객 가치 분석
{json.dumps(rfm, indent=2, default=str)}

## K-Means 행동 기반 세그멘테이션
{json.dumps(segmentation, indent=2, default=str)}

## 상품 카테고리 분석
{json.dumps(product, indent=2, default=str)}

## 실시간 서비스 데이터
- 총 URL: {realtime_data.get('total_urls', 0)}개
- 총 클릭: {realtime_data.get('total_clicks', 0)}회
- 국가별: {json.dumps(realtime_data.get('country_distribution', {}), indent=2)}

다음 형식으로 분석 결과를 제공해주세요:

### 1. 고객 세그먼트 종합 분석
(RFM과 K-Means 결과를 교차 분석하여 핵심 고객 그룹 정의)

### 2. 세그먼트별 맞춤 마케팅 전략
(각 세그먼트에 어떤 메시지, 채널, 타이밍으로 접근해야 하는지)

### 3. 이탈 위험 고객 관리 방안
(At Risk, Lost 세그먼트에 대한 리텐션 전략)

### 4. 고가치 고객 육성 전략
(Champions, Loyal → 더 높은 가치로 전환하는 방법)

### 5. 상품 추천 전략
(세그먼트별 추천 카테고리/상품)

### 6. 즉시 실행 가능한 CRM 액션 아이템 5가지

한국어로 실용적이고 구체적으로 답변해주세요. 숫자와 데이터를 근거로 제시해주세요.
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
        session_data = body.get('session', {})

        # 2. 데이터 수집
        realtime_data = get_realtime_stats_from_dynamodb() or {
            'total_urls': 0, 'total_clicks': 0,
            'referer_distribution': {}, 'device_distribution': {},
            'country_distribution': {}, 'hourly_distribution': {}
        }

        insights_data = load_insights_from_s3()

        # 3. 모델 로드 & 전환 예측
        model, metadata = load_model_from_s3()
        conversion_prob = predict_conversion(model, metadata, session_data)

        # 4. 분석 타입별 프롬프트 생성
        if analysis_type == 'traffic':
            prompt = build_traffic_prompt(realtime_data, insights_data)
        elif analysis_type == 'conversion':
            prompt = build_conversion_prompt(realtime_data, insights_data, conversion_prob)
        elif analysis_type == 'segmentation':
            prompt = build_segmentation_prompt(realtime_data, insights_data)
        else:  # full
            prompt = build_full_prompt(realtime_data, insights_data, conversion_prob)

        # 5. Bedrock 호출
        ai_response = invoke_bedrock(prompt)

        # 6. 응답 반환
        # RFM/세그멘테이션 요약 정보 포함
        rfm_summary = None
        segmentation_summary = None
        product_summary = None

        if insights_data:
            rfm_data = insights_data.get('rfm_analysis', {})
            if rfm_data and rfm_data.get('segments'):
                rfm_summary = {
                    'total_customers': rfm_data.get('summary', {}).get('total_customers'),
                    'segments': {k: {'count': v['count'], 'percentage': v['percentage']}
                                 for k, v in rfm_data['segments'].items()},
                }

            seg_data = insights_data.get('customer_segmentation', {})
            if seg_data and seg_data.get('clusters'):
                segmentation_summary = {
                    'n_clusters': seg_data.get('n_clusters'),
                    'clusters': {k: {'count': v['count'], 'percentage': v['percentage']}
                                 for k, v in seg_data['clusters'].items()},
                }

            prod_data = insights_data.get('product_analysis', {})
            if prod_data and prod_data.get('categories'):
                product_summary = {
                    'total_products': prod_data.get('summary', {}).get('total_products'),
                    'total_revenue': prod_data.get('summary', {}).get('total_revenue'),
                    'top_categories': list(prod_data['categories'].keys())[:5],
                }

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
                'loaded': model is not None,
                'type': 'xgboost + kmeans + rfm',
                'accuracy': metadata.get('metrics', {}).get('accuracy') if metadata else None,
                'auc_roc': metadata.get('metrics', {}).get('auc_roc') if metadata else None,
                'trained_at': metadata.get('trained_at') if metadata else None,
            },
            'conversion_prediction': {
                'probability': conversion_prob,
                'label': 'high' if conversion_prob and conversion_prob > 0.5 else 'low',
            } if conversion_prob else None,
            'rfm_summary': rfm_summary,
            'segmentation_summary': segmentation_summary,
            'product_summary': product_summary,
            'ai_insights': ai_response,
            'generated_at': datetime.utcnow().isoformat(),
            'data_source': 'realtime+model+rfm+segmentation' if model else 'realtime'
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
