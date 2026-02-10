"""
로컬에서 XGBoost + 고객 세그멘테이션 + RFM 분석 후 S3에 업로드
SageMaker Endpoint 없이 Lambda에서 직접 모델을 로드하여 예측


비용: S3 저장 비용만 발생 (거의 $0)
"""

import pandas as pd
import numpy as np
import xgboost as xgb
import boto3
import argparse
import json
import os
import pickle
import tempfile
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


# ============================================================
# 1. 데이터 로드
# ============================================================

def load_all_data():
    """datasets 폴더에서 e-commerce 데이터 전부 로드"""
    base_path = os.path.join(os.path.dirname(__file__), '../../datasets/archive(e-commerce)')

    print("  데이터 로드 중...")
    events = pd.read_csv(os.path.join(base_path, 'events.csv'))
    sessions = pd.read_csv(os.path.join(base_path, 'sessions.csv'))
    orders = pd.read_csv(os.path.join(base_path, 'orders.csv'))
    customers = pd.read_csv(os.path.join(base_path, 'customers.csv'))
    products = pd.read_csv(os.path.join(base_path, 'products.csv'))
    reviews = pd.read_csv(os.path.join(base_path, 'reviews.csv'))
    order_items = pd.read_csv(os.path.join(base_path, 'order_items.csv'))

    print(f"  - Events:      {len(events):>10,} rows")
    print(f"  - Sessions:    {len(sessions):>10,} rows")
    print(f"  - Orders:      {len(orders):>10,} rows")
    print(f"  - Customers:   {len(customers):>10,} rows")
    print(f"  - Products:    {len(products):>10,} rows")
    print(f"  - Reviews:     {len(reviews):>10,} rows")
    print(f"  - Order Items: {len(order_items):>10,} rows")

    return events, sessions, orders, customers, products, reviews, order_items


# ============================================================
# 2. XGBoost 전환 예측 모델
# ============================================================

def prepare_conversion_features(events, sessions, customers):
    """전환 예측용 피처 엔지니어링"""
    print("  전환 예측 피처 생성 중...")

    # 세션별 이벤트 집계
    session_agg = events.groupby('session_id').agg(
        total_events=('event_id', 'count'),
        page_views=('event_type', lambda x: (x == 'page_view').sum()),
        add_to_cart=('event_type', lambda x: (x == 'add_to_cart').sum()),
        purchases=('event_type', lambda x: (x == 'purchase').sum()),
        unique_products=('product_id', 'nunique'),
        first_event=('timestamp', 'min'),
        last_event=('timestamp', 'max'),
    ).reset_index()

    session_agg['purchased'] = (session_agg['purchases'] > 0).astype(int)
    session_agg['first_event'] = pd.to_datetime(session_agg['first_event'])
    session_agg['last_event'] = pd.to_datetime(session_agg['last_event'])
    session_agg['session_duration_min'] = (
        (session_agg['last_event'] - session_agg['first_event']).dt.total_seconds() / 60
    )
    session_agg['hour'] = session_agg['first_event'].dt.hour
    session_agg['day_of_week'] = session_agg['first_event'].dt.dayofweek
    session_agg['is_weekend'] = (session_agg['day_of_week'] >= 5).astype(int)

    # 세션 + 고객 정보 조인
    df = session_agg.merge(sessions, on='session_id', how='left')
    df = df.merge(customers[['customer_id', 'age', 'marketing_opt_in']], on='customer_id', how='left')

    # 인코딩
    df['device_encoded'] = df['device'].map({'desktop': 0, 'mobile': 1, 'tablet': 2}).fillna(0)
    df['source_encoded'] = df['source'].map({'direct': 0, 'organic': 1, 'email': 2, 'paid': 3}).fillna(0)
    df['marketing_opt_in'] = df['marketing_opt_in'].map({True: 1, False: 0, 'True': 1, 'False': 0}).fillna(0)

    feature_cols = [
        'total_events', 'page_views', 'add_to_cart', 'unique_products',
        'session_duration_min', 'hour', 'day_of_week', 'is_weekend',
        'device_encoded', 'source_encoded', 'age', 'marketing_opt_in'
    ]

    df_clean = df[feature_cols + ['purchased']].dropna()
    print(f"  - 데이터: {len(df_clean):,} rows, {len(feature_cols)} features")
    print(f"  - 구매 비율: {df_clean['purchased'].mean():.2%}")

    return df_clean, feature_cols


def train_xgboost(df, feature_cols):
    """XGBoost 모델 학습"""
    print("  XGBoost 학습 중...")

    X = df[feature_cols]
    y = df['purchased']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        objective='binary:logistic',
        n_estimators=100,
        max_depth=5,
        learning_rate=0.2,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric='auc',
        random_state=42,
        use_label_encoder=False,
    )

    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)

    print(f"\n  === XGBoost 성능 ===")
    print(f"  Accuracy: {accuracy:.4f}")
    print(f"  AUC-ROC:  {auc:.4f}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['Not Purchased', 'Purchased'])}")

    importance = dict(zip(feature_cols, model.feature_importances_))
    importance_sorted = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    print("  === Feature Importance ===")
    for feat, imp in importance_sorted:
        bar = '#' * int(imp * 50)
        print(f"  {feat:25s} {imp:.4f} {bar}")

    metrics = {
        'accuracy': float(accuracy),
        'auc_roc': float(auc),
        'feature_importance': {k: float(v) for k, v in importance.items()},
        'feature_columns': feature_cols,
        'train_size': len(X_train),
        'test_size': len(X_test),
    }

    return model, metrics


# ============================================================
# 3. RFM 분석 (Recency, Frequency, Monetary)
# ============================================================

def analyze_rfm(orders, customers):
    """RFM 분석으로 고객 가치 분류"""
    print("  RFM 분석 중...")

    orders['order_time'] = pd.to_datetime(orders['order_time'])
    reference_date = orders['order_time'].max() + pd.Timedelta(days=1)

    # 고객별 RFM 계산
    rfm = orders.groupby('customer_id').agg(
        recency=('order_time', lambda x: (reference_date - x.max()).days),
        frequency=('order_id', 'nunique'),
        monetary=('total_usd', 'sum'),
    ).reset_index()

    # RFM 스코어 (1~5)
    rfm['r_score'] = pd.qcut(rfm['recency'], q=5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm['f_score'] = pd.qcut(rfm['frequency'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm['m_score'] = pd.qcut(rfm['monetary'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm['rfm_score'] = rfm['r_score'] * 100 + rfm['f_score'] * 10 + rfm['m_score']

    # 고객 세그먼트 분류
    def classify_customer(row):
        r, f, m = row['r_score'], row['f_score'], row['m_score']
        if r >= 4 and f >= 4 and m >= 4:
            return 'Champions'
        elif r >= 3 and f >= 3:
            return 'Loyal Customers'
        elif r >= 4 and f <= 2:
            return 'New Customers'
        elif r >= 3 and f >= 1 and m >= 3:
            return 'Potential Loyalists'
        elif r <= 2 and f >= 3 and m >= 3:
            return 'At Risk'
        elif r <= 2 and f >= 4:
            return 'Cant Lose Them'
        elif r <= 2 and f <= 2:
            return 'Lost'
        elif r >= 3 and f <= 2 and m <= 2:
            return 'Promising'
        else:
            return 'Need Attention'

    rfm['segment'] = rfm.apply(classify_customer, axis=1)

    # 고객 정보 조인
    rfm = rfm.merge(customers[['customer_id', 'country', 'age', 'marketing_opt_in']], on='customer_id', how='left')

    # 통계
    segment_stats = rfm.groupby('segment').agg(
        count=('customer_id', 'count'),
        avg_recency=('recency', 'mean'),
        avg_frequency=('frequency', 'mean'),
        avg_monetary=('monetary', 'mean'),
        avg_age=('age', 'mean'),
    ).reset_index()

    segment_stats['count_pct'] = (segment_stats['count'] / segment_stats['count'].sum() * 100).round(1)

    print(f"\n  === RFM 세그먼트 분포 ===")
    for _, row in segment_stats.sort_values('count', ascending=False).iterrows():
        bar = '#' * int(row['count_pct'] * 2)
        print(f"  {row['segment']:20s} {row['count']:>5} ({row['count_pct']:>5.1f}%) {bar}")

    rfm_insights = {
        'segments': {},
        'summary': {
            'total_customers': len(rfm),
            'avg_recency': float(rfm['recency'].mean()),
            'avg_frequency': float(rfm['frequency'].mean()),
            'avg_monetary': float(rfm['monetary'].mean()),
        }
    }

    for _, row in segment_stats.iterrows():
        rfm_insights['segments'][row['segment']] = {
            'count': int(row['count']),
            'percentage': float(row['count_pct']),
            'avg_recency_days': round(float(row['avg_recency']), 1),
            'avg_orders': round(float(row['avg_frequency']), 1),
            'avg_spending_usd': round(float(row['avg_monetary']), 2),
            'avg_age': round(float(row['avg_age']), 1),
        }

    # 세그먼트별 국가 분포
    country_by_segment = {}
    for segment in rfm['segment'].unique():
        seg_data = rfm[rfm['segment'] == segment]
        top_countries = seg_data['country'].value_counts().head(5).to_dict()
        country_by_segment[segment] = {k: int(v) for k, v in top_countries.items()}
    rfm_insights['country_by_segment'] = country_by_segment

    return rfm, rfm_insights


# ============================================================
# 4. 고객 세그멘테이션 (K-Means 클러스터링)
# ============================================================

def segment_customers_kmeans(orders, sessions, events, customers, products, order_items, reviews):
    """K-Means 클러스터링으로 고객 행동 세그멘테이션"""
    print("  K-Means 세그멘테이션 중...")

    # --- 고객별 행동 피처 생성 ---

    # 주문 기반 피처
    order_features = orders.groupby('customer_id').agg(
        total_orders=('order_id', 'nunique'),
        total_spent=('total_usd', 'sum'),
        avg_order_value=('total_usd', 'mean'),
        avg_discount=('discount_pct', 'mean'),
    ).reset_index()

    # 세션 기반 피처
    session_features = sessions.groupby('customer_id').agg(
        total_sessions=('session_id', 'nunique'),
    ).reset_index()

    # 이벤트 기반 피처 (세션 경유)
    events_with_customer = events.merge(sessions[['session_id', 'customer_id']], on='session_id', how='left')
    event_features = events_with_customer.groupby('customer_id').agg(
        total_events=('event_id', 'count'),
        total_page_views=('event_type', lambda x: (x == 'page_view').sum()),
        total_add_to_cart=('event_type', lambda x: (x == 'add_to_cart').sum()),
        total_purchases_events=('event_type', lambda x: (x == 'purchase').sum()),
        unique_products_viewed=('product_id', 'nunique'),
    ).reset_index()

    # 디바이스 선호도
    device_pref = sessions.groupby('customer_id')['device'].agg(
        lambda x: x.value_counts().index[0] if len(x) > 0 else 'unknown'
    ).reset_index()
    device_pref.columns = ['customer_id', 'preferred_device']

    # 유입 채널 선호도
    source_pref = sessions.groupby('customer_id')['source'].agg(
        lambda x: x.value_counts().index[0] if len(x) > 0 else 'unknown'
    ).reset_index()
    source_pref.columns = ['customer_id', 'preferred_source']

    # 리뷰 기반 피처
    review_features = reviews.merge(orders[['order_id', 'customer_id']], on='order_id', how='left')
    review_agg = review_features.groupby('customer_id').agg(
        total_reviews=('review_id', 'count'),
        avg_rating=('rating', 'mean'),
    ).reset_index()

    # 상품 카테고리 선호도
    items_with_products = order_items.merge(products[['product_id', 'category', 'price_usd']], on='product_id', how='left')
    items_with_customer = items_with_products.merge(orders[['order_id', 'customer_id']], on='order_id', how='left')
    category_diversity = items_with_customer.groupby('customer_id').agg(
        unique_categories=('category', 'nunique'),
        avg_product_price=('price_usd', 'mean'),
    ).reset_index()

    # --- 모든 피처 합치기 ---
    customer_df = customers[['customer_id', 'age', 'marketing_opt_in', 'country']].copy()
    customer_df = customer_df.merge(order_features, on='customer_id', how='left')
    customer_df = customer_df.merge(session_features, on='customer_id', how='left')
    customer_df = customer_df.merge(event_features, on='customer_id', how='left')
    customer_df = customer_df.merge(device_pref, on='customer_id', how='left')
    customer_df = customer_df.merge(source_pref, on='customer_id', how='left')
    customer_df = customer_df.merge(review_agg, on='customer_id', how='left')
    customer_df = customer_df.merge(category_diversity, on='customer_id', how='left')

    customer_df = customer_df.fillna(0)
    customer_df['marketing_opt_in'] = customer_df['marketing_opt_in'].map(
        {True: 1, False: 0, 'True': 1, 'False': 0, 1: 1, 0: 0}
    ).fillna(0)

    # --- K-Means 클러스터링 ---
    numeric_features = [
        'age', 'total_orders', 'total_spent', 'avg_order_value', 'avg_discount',
        'total_sessions', 'total_events', 'total_page_views', 'total_add_to_cart',
        'unique_products_viewed', 'total_reviews', 'avg_rating',
        'unique_categories', 'avg_product_price'
    ]

    X = customer_df[numeric_features].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # K=4 클러스터
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    customer_df['cluster'] = kmeans.fit_predict(X_scaled)

    # --- 클러스터 해석 ---
    cluster_profiles = customer_df.groupby('cluster').agg(
        count=('customer_id', 'count'),
        avg_age=('age', 'mean'),
        avg_orders=('total_orders', 'mean'),
        avg_spent=('total_spent', 'mean'),
        avg_sessions=('total_sessions', 'mean'),
        avg_page_views=('total_page_views', 'mean'),
        avg_cart_adds=('total_add_to_cart', 'mean'),
        avg_reviews=('total_reviews', 'mean'),
        avg_rating=('avg_rating', 'mean'),
        avg_categories=('unique_categories', 'mean'),
        marketing_opt_in_rate=('marketing_opt_in', 'mean'),
    ).reset_index()

    # 클러스터 이름 부여 (특성 기반)
    cluster_names = {}
    for _, row in cluster_profiles.iterrows():
        c = int(row['cluster'])
        if row['avg_spent'] > cluster_profiles['avg_spent'].median() and row['avg_orders'] > cluster_profiles['avg_orders'].median():
            cluster_names[c] = 'High-Value Active'
        elif row['avg_sessions'] > cluster_profiles['avg_sessions'].median() and row['avg_orders'] <= cluster_profiles['avg_orders'].median():
            cluster_names[c] = 'Window Shoppers'
        elif row['avg_spent'] <= cluster_profiles['avg_spent'].quantile(0.25):
            cluster_names[c] = 'Low Engagement'
        else:
            cluster_names[c] = 'Growing Potential'

    # 중복 이름 처리
    used_names = set()
    for c in sorted(cluster_names.keys()):
        name = cluster_names[c]
        if name in used_names:
            cluster_names[c] = name + f' ({c})'
        used_names.add(cluster_names[c])

    customer_df['cluster_name'] = customer_df['cluster'].map(cluster_names)

    print(f"\n  === K-Means 클러스터 프로필 ===")
    for _, row in cluster_profiles.iterrows():
        c = int(row['cluster'])
        name = cluster_names.get(c, f'Cluster {c}')
        print(f"\n  [{name}] ({int(row['count']):,} customers)")
        print(f"    Avg Age: {row['avg_age']:.0f} | Orders: {row['avg_orders']:.1f} | Spent: ${row['avg_spent']:.0f}")
        print(f"    Sessions: {row['avg_sessions']:.1f} | Page Views: {row['avg_page_views']:.0f} | Cart Adds: {row['avg_cart_adds']:.1f}")
        print(f"    Reviews: {row['avg_reviews']:.1f} | Avg Rating: {row['avg_rating']:.1f} | Categories: {row['avg_categories']:.1f}")
        print(f"    Marketing Opt-in: {row['marketing_opt_in_rate']:.1%}")

    # 인사이트 생성
    segmentation_insights = {
        'n_clusters': 4,
        'cluster_names': cluster_names,
        'clusters': {},
    }

    for _, row in cluster_profiles.iterrows():
        c = int(row['cluster'])
        name = cluster_names.get(c, f'Cluster {c}')

        # 클러스터별 디바이스/채널 분포
        cluster_data = customer_df[customer_df['cluster'] == c]
        device_dist = cluster_data['preferred_device'].value_counts().to_dict()
        source_dist = cluster_data['preferred_source'].value_counts().to_dict()
        top_countries = cluster_data['country'].value_counts().head(5).to_dict()

        segmentation_insights['clusters'][name] = {
            'count': int(row['count']),
            'percentage': round(float(row['count'] / len(customer_df) * 100), 1),
            'avg_age': round(float(row['avg_age']), 1),
            'avg_orders': round(float(row['avg_orders']), 1),
            'avg_spending_usd': round(float(row['avg_spent']), 2),
            'avg_sessions': round(float(row['avg_sessions']), 1),
            'avg_page_views': round(float(row['avg_page_views']), 1),
            'avg_cart_adds': round(float(row['avg_cart_adds']), 1),
            'avg_reviews': round(float(row['avg_reviews']), 1),
            'avg_rating': round(float(row['avg_rating']), 2),
            'unique_categories': round(float(row['avg_categories']), 1),
            'marketing_opt_in_rate': round(float(row['marketing_opt_in_rate']), 3),
            'preferred_devices': {k: int(v) for k, v in device_dist.items()},
            'preferred_sources': {k: int(v) for k, v in source_dist.items()},
            'top_countries': {k: int(v) for k, v in top_countries.items()},
        }

    return kmeans, scaler, numeric_features, segmentation_insights


# ============================================================
# 5. 상품 & 카테고리 분석
# ============================================================

def analyze_products(products, order_items, orders, reviews):
    """상품 및 카테고리 인사이트"""
    print("  상품 분석 중...")

    # 카테고리별 매출
    items = order_items.merge(products[['product_id', 'category', 'price_usd', 'margin_usd']], on='product_id', how='left')
    items = items.merge(orders[['order_id', 'customer_id', 'device', 'source']], on='order_id', how='left')

    category_stats = items.groupby('category').agg(
        total_sold=('quantity', 'sum'),
        total_revenue=('line_total_usd', 'sum'),
        unique_customers=('customer_id', 'nunique'),
        avg_price=('price_usd', 'mean'),
        total_margin=('margin_usd', lambda x: (x * items.loc[x.index, 'quantity']).sum()),
    ).reset_index()
    category_stats = category_stats.sort_values('total_revenue', ascending=False)

    # 카테고리별 디바이스/채널
    category_device = items.groupby(['category', 'device']).agg(
        count=('order_id', 'count')
    ).reset_index()
    category_source = items.groupby(['category', 'source']).agg(
        count=('order_id', 'count')
    ).reset_index()

    # 리뷰 분석
    review_with_product = reviews.merge(products[['product_id', 'category']], on='product_id', how='left')
    category_reviews = review_with_product.groupby('category').agg(
        avg_rating=('rating', 'mean'),
        total_reviews=('review_id', 'count'),
    ).reset_index()

    print(f"\n  === 카테고리별 매출 ===")
    for _, row in category_stats.iterrows():
        print(f"  {row['category']:20s} ${row['total_revenue']:>12,.0f} ({int(row['total_sold']):>6,} sold)")

    product_insights = {
        'categories': {},
        'summary': {
            'total_products': len(products),
            'total_categories': len(category_stats),
            'total_revenue': float(category_stats['total_revenue'].sum()),
        }
    }

    for _, row in category_stats.iterrows():
        cat = row['category']
        review_row = category_reviews[category_reviews['category'] == cat]
        avg_rating = float(review_row['avg_rating'].values[0]) if len(review_row) > 0 else 0

        # 카테고리별 디바이스 분포
        dev_data = category_device[category_device['category'] == cat]
        dev_dist = {r['device']: int(r['count']) for _, r in dev_data.iterrows()}

        # 카테고리별 채널 분포
        src_data = category_source[category_source['category'] == cat]
        src_dist = {r['source']: int(r['count']) for _, r in src_data.iterrows()}

        product_insights['categories'][cat] = {
            'total_sold': int(row['total_sold']),
            'total_revenue_usd': round(float(row['total_revenue']), 2),
            'unique_customers': int(row['unique_customers']),
            'avg_price_usd': round(float(row['avg_price']), 2),
            'avg_rating': round(avg_rating, 2),
            'device_distribution': dev_dist,
            'source_distribution': src_dist,
        }

    return product_insights


# ============================================================
# 6. 종합 인사이트 생성
# ============================================================

def generate_comprehensive_insights(df, feature_cols, xgb_metrics, rfm_insights,
                                     segmentation_insights, product_insights,
                                     events, sessions):
    """모든 분석 결과를 종합 인사이트로 합치기"""
    print("  종합 인사이트 생성 중...")

    # 디바이스별 전환율
    device_conv = {}
    for device_code, device_name in [(0, 'desktop'), (1, 'mobile'), (2, 'tablet')]:
        subset = df[df['device_encoded'] == device_code]
        if len(subset) > 0:
            device_conv[device_name] = {
                'sessions': int(len(subset)),
                'conversion_rate': round(float(subset['purchased'].mean()), 4),
            }

    # 채널별 전환율
    source_conv = {}
    for source_code, source_name in [(0, 'direct'), (1, 'organic'), (2, 'email'), (3, 'paid')]:
        subset = df[df['source_encoded'] == source_code]
        if len(subset) > 0:
            source_conv[source_name] = {
                'sessions': int(len(subset)),
                'conversion_rate': round(float(subset['purchased'].mean()), 4),
            }

    # 시간대별 전환율
    hourly_conv = {}
    for h in range(24):
        subset = df[df['hour'] == h]
        if len(subset) > 0:
            hourly_conv[str(h)] = round(float(subset['purchased'].mean()), 4)

    # 요일별 전환율
    daily_conv = {}
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for d in range(7):
        subset = df[df['day_of_week'] == d]
        if len(subset) > 0:
            daily_conv[day_names[d]] = round(float(subset['purchased'].mean()), 4)

    insights = {
        'generated_at': datetime.utcnow().isoformat(),
        'data_summary': {
            'total_sessions': int(len(df)),
            'conversion_rate': round(float(df['purchased'].mean()), 4),
            'avg_page_views': round(float(df['page_views'].mean()), 2),
            'avg_session_duration_min': round(float(df['session_duration_min'].mean()), 2),
            'avg_events_per_session': round(float(df['total_events'].mean()), 2),
        },
        'model_performance': xgb_metrics,
        'device_analysis': device_conv,
        'source_analysis': source_conv,
        'hourly_conversion': hourly_conv,
        'daily_conversion': daily_conv,
        'rfm_analysis': rfm_insights,
        'customer_segmentation': segmentation_insights,
        'product_analysis': product_insights,
    }

    return insights


# ============================================================
# 7. S3 업로드
# ============================================================

def upload_to_s3(bucket, model, kmeans_model, scaler, feature_cols, kmeans_features,
                 metrics, insights):
    """모델과 인사이트를 S3에 업로드"""
    print("  S3 업로드 중...")
    s3 = boto3.client('s3')

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. XGBoost 모델
        model_path = os.path.join(tmpdir, 'model.pkl')
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        s3.upload_file(model_path, bucket, 'model/model.pkl')
        print(f"  - s3://{bucket}/model/model.pkl")

        # 2. K-Means 모델 + Scaler
        kmeans_path = os.path.join(tmpdir, 'kmeans.pkl')
        with open(kmeans_path, 'wb') as f:
            pickle.dump({'kmeans': kmeans_model, 'scaler': scaler, 'features': kmeans_features}, f)
        s3.upload_file(kmeans_path, bucket, 'model/kmeans.pkl')
        print(f"  - s3://{bucket}/model/kmeans.pkl")

        # 3. 모델 메타데이터
        metadata = {
            'feature_columns': feature_cols,
            'kmeans_features': kmeans_features,
            'model_type': 'xgboost + kmeans',
            'trained_at': datetime.utcnow().isoformat(),
            'metrics': metrics,
        }
        s3.put_object(
            Bucket=bucket, Key='model/metadata.json',
            Body=json.dumps(metadata, indent=2), ContentType='application/json'
        )
        print(f"  - s3://{bucket}/model/metadata.json")

        # 4. 종합 인사이트
        s3.put_object(
            Bucket=bucket, Key='processed-data/insights.json',
            Body=json.dumps(insights, indent=2, default=str), ContentType='application/json'
        )
        print(f"  - s3://{bucket}/processed-data/insights.json")

        # 5. summary.json (Bedrock 프롬프트용)
        s3.put_object(
            Bucket=bucket, Key='processed-data/summary.json',
            Body=json.dumps(insights, indent=2, default=str), ContentType='application/json'
        )
        print(f"  - s3://{bucket}/processed-data/summary.json")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='XGBoost + 세그멘테이션 + RFM 학습')
    parser.add_argument('--bucket', required=True, help='S3 버킷 이름')
    args = parser.parse_args()

    print("=" * 60)
    print("  LinkSnap AI - 종합 분석 & 모델 학습")
    print("  (XGBoost + K-Means + RFM)")
    print("=" * 60)

    # 1. 데이터 로드
    print("\n[1/6] 데이터 로드")
    events, sessions, orders, customers, products, reviews, order_items = load_all_data()

    # 2. XGBoost 전환 예측
    print("\n[2/6] XGBoost 전환 예측 모델")
    df, feature_cols = prepare_conversion_features(events, sessions, customers)
    xgb_model, xgb_metrics = train_xgboost(df, feature_cols)

    # 3. RFM 분석
    print("\n[3/6] RFM 분석")
    rfm_df, rfm_insights = analyze_rfm(orders, customers)

    # 4. K-Means 세그멘테이션
    print("\n[4/6] K-Means 고객 세그멘테이션")
    kmeans_model, scaler, kmeans_features, seg_insights = segment_customers_kmeans(
        orders, sessions, events, customers, products, order_items, reviews
    )

    # 5. 상품 분석
    print("\n[5/6] 상품 & 카테고리 분석")
    product_insights = analyze_products(products, order_items, orders, reviews)

    # 6. 종합 인사이트 + S3 업로드
    print("\n[6/6] 종합 인사이트 생성 & S3 업로드")
    insights = generate_comprehensive_insights(
        df, feature_cols, xgb_metrics, rfm_insights,
        seg_insights, product_insights, events, sessions
    )
    upload_to_s3(
        args.bucket, xgb_model, kmeans_model, scaler,
        feature_cols, kmeans_features, xgb_metrics, insights
    )

    print("\n" + "=" * 60)
    print("  모든 분석 완료!")
    print("=" * 60)
    print(f"\n  S3 버킷: {args.bucket}")
    print(f"  모델: model/model.pkl (XGBoost), model/kmeans.pkl (K-Means)")
    print(f"  인사이트: processed-data/insights.json")
    print(f"\n  다음 단계:")
    print(f"  1. bash build_layer.sh       # Lambda Layer 빌드")
    print(f"  2. cd ../terraform-ai")
    print(f"  3. terraform apply           # Lambda 배포")
    print("=" * 60)


if __name__ == '__main__':
    main()
