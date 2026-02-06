"""
datasets 폴더의 데이터를 SageMaker 학습용으로 전처리하는 스크립트

사용법:
    python prepare_data.py --bucket {S3_BUCKET_NAME}
"""

import pandas as pd
import numpy as np
import boto3
import argparse
import os
from datetime import datetime
from io import StringIO

def load_ecommerce_data():
    """e-commerce 데이터 로드"""
    base_path = os.path.join(os.path.dirname(__file__), '../../datasets/archive(e-commerce)')
    
    events = pd.read_csv(os.path.join(base_path, 'events.csv'))
    sessions = pd.read_csv(os.path.join(base_path, 'sessions.csv'))
    
    print(f"Events: {len(events)} rows")
    print(f"Sessions: {len(sessions)} rows")
    
    return events, sessions


def load_clickstream_data():
    """clickstream 데이터 로드"""
    path = os.path.join(
        os.path.dirname(__file__), 
        '../../datasets/clickstream_onlineshopping2008/e-shop clothing 2008.csv'
    )
    
    df = pd.read_csv(path, sep=';')
    print(f"Clickstream: {len(df)} rows")
    
    return df


def prepare_traffic_pattern_data(events, sessions):
    """
    트래픽 패턴 분석용 데이터 준비
    - 시간대별 트래픽
    - 유입 경로별 트래픽
    - 디바이스별 트래픽
    """
    # events에 session 정보 조인
    df = events.merge(sessions, on='session_id', how='left')
    
    # timestamp 파싱
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['date'] = df['timestamp'].dt.date
    
    # 시간대별 트래픽 집계
    hourly_traffic = df.groupby(['date', 'hour']).agg({
        'event_id': 'count',
        'session_id': 'nunique'
    }).reset_index()
    hourly_traffic.columns = ['date', 'hour', 'event_count', 'unique_sessions']
    
    # 유입 경로별 집계
    source_traffic = df.groupby(['date', 'source']).agg({
        'event_id': 'count',
        'session_id': 'nunique'
    }).reset_index()
    source_traffic.columns = ['date', 'source', 'event_count', 'unique_sessions']
    
    # 디바이스별 집계
    device_traffic = df.groupby(['date', 'device']).agg({
        'event_id': 'count',
        'session_id': 'nunique'
    }).reset_index()
    device_traffic.columns = ['date', 'device', 'event_count', 'unique_sessions']
    
    return hourly_traffic, source_traffic, device_traffic


def prepare_conversion_data(events, sessions):
    """
    구매 전환 예측용 데이터 준비
    - 세션별 특성
    - 구매 여부 (target)
    """
    # 세션별 이벤트 집계
    session_events = events.groupby('session_id').agg({
        'event_id': 'count',
        'event_type': lambda x: list(x),
        'timestamp': ['min', 'max']
    }).reset_index()
    session_events.columns = ['session_id', 'total_events', 'event_sequence', 'first_event', 'last_event']
    
    # 구매 여부
    session_events['purchased'] = session_events['event_sequence'].apply(
        lambda x: 1 if 'purchase' in x else 0
    )
    
    # 장바구니 추가 여부
    session_events['added_to_cart'] = session_events['event_sequence'].apply(
        lambda x: 1 if 'add_to_cart' in x else 0
    )
    
    # 페이지뷰 수
    session_events['page_views'] = session_events['event_sequence'].apply(
        lambda x: x.count('page_view')
    )
    
    # 세션 정보 조인
    df = session_events.merge(sessions, on='session_id', how='left')
    
    # 세션 지속 시간
    df['first_event'] = pd.to_datetime(df['first_event'])
    df['last_event'] = pd.to_datetime(df['last_event'])
    df['session_duration_min'] = (df['last_event'] - df['first_event']).dt.total_seconds() / 60
    
    # 시간 특성
    df['hour'] = df['first_event'].dt.hour
    df['day_of_week'] = df['first_event'].dt.dayofweek
    
    # 필요한 컬럼만 선택
    features = ['session_id', 'total_events', 'page_views', 'added_to_cart', 
                'session_duration_min', 'hour', 'day_of_week', 'device', 'source', 'country',
                'purchased']  # target
    
    df = df[features].dropna()
    
    # 범주형 변수 인코딩
    df['device_encoded'] = df['device'].map({'desktop': 0, 'mobile': 1, 'tablet': 2})
    df['source_encoded'] = df['source'].map({'direct': 0, 'organic': 1, 'email': 2, 'paid': 3})
    
    return df


def prepare_xgboost_data(df):
    """XGBoost 학습용 CSV 형식으로 변환 (target이 첫 번째 컬럼)"""
    # 수치형 특성만 선택
    numeric_features = ['purchased', 'total_events', 'page_views', 'added_to_cart',
                        'session_duration_min', 'hour', 'day_of_week', 
                        'device_encoded', 'source_encoded']
    
    df_numeric = df[numeric_features].dropna()
    
    # Train/Test 분할
    train_size = int(len(df_numeric) * 0.8)
    train_df = df_numeric[:train_size]
    test_df = df_numeric[train_size:]
    
    return train_df, test_df


def upload_to_s3(df, bucket, key):
    """DataFrame을 S3에 CSV로 업로드"""
    s3 = boto3.client('s3')
    
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False, header=False)  # XGBoost는 헤더 없이
    
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=csv_buffer.getvalue()
    )
    print(f"Uploaded to s3://{bucket}/{key}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bucket', required=True, help='S3 버킷 이름')
    args = parser.parse_args()
    
    print("=" * 50)
    print("데이터 전처리 시작")
    print("=" * 50)
    
    # 1. 데이터 로드
    print("\n[1/4] 데이터 로드 중...")
    events, sessions = load_ecommerce_data()
    
    # 2. 트래픽 패턴 데이터 준비
    print("\n[2/4] 트래픽 패턴 데이터 준비 중...")
    hourly, source, device = prepare_traffic_pattern_data(events, sessions)
    
    # 3. 전환 예측 데이터 준비
    print("\n[3/4] 전환 예측 데이터 준비 중...")
    conversion_df = prepare_conversion_data(events, sessions)
    train_df, test_df = prepare_xgboost_data(conversion_df)
    
    print(f"  - Train: {len(train_df)} rows")
    print(f"  - Test: {len(test_df)} rows")
    
    # 4. S3 업로드
    print("\n[4/4] S3 업로드 중...")
    
    # 트래픽 데이터
    upload_to_s3(hourly, args.bucket, 'processed-data/traffic/hourly.csv')
    upload_to_s3(source, args.bucket, 'processed-data/traffic/source.csv')
    upload_to_s3(device, args.bucket, 'processed-data/traffic/device.csv')
    
    # XGBoost 학습 데이터
    upload_to_s3(train_df, args.bucket, 'training-data/train.csv')
    upload_to_s3(test_df, args.bucket, 'training-data/test.csv')
    
    # 통계 요약 저장
    summary = {
        'total_sessions': len(sessions),
        'total_events': len(events),
        'conversion_rate': conversion_df['purchased'].mean(),
        'avg_page_views': conversion_df['page_views'].mean(),
        'top_sources': source.groupby('source')['event_count'].sum().to_dict(),
        'top_devices': device.groupby('device')['event_count'].sum().to_dict()
    }
    
    import json
    s3 = boto3.client('s3')
    s3.put_object(
        Bucket=args.bucket,
        Key='processed-data/summary.json',
        Body=json.dumps(summary, indent=2, default=str)
    )
    print(f"Uploaded summary to s3://{args.bucket}/processed-data/summary.json")
    
    print("\n" + "=" * 50)
    print("데이터 전처리 완료!")
    print("=" * 50)
    print(f"\n다음 단계: terraform apply로 SageMaker Training Job 실행")


if __name__ == '__main__':
    main()
