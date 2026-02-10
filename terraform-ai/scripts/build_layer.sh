#!/bin/bash
# XGBoost + scikit-learn Lambda Layer 빌드 스크립트
# pip로 빌드 → S3 업로드 
# 포함: xgboost, scikit-learn, numpy, scipy (K-Means 클러스터링용)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LAYER_DIR="$PROJECT_DIR/modules/bedrock_lambda/builds"
TEMP_DIR=$(mktemp -d)

# S3 버킷 이름 (terraform output에서 가져오기)
S3_BUCKET=$(cd "$PROJECT_DIR" && terraform output -raw s3_bucket_name 2>/dev/null)
if [ -z "$S3_BUCKET" ]; then
    echo "S3 버킷을 찾을 수 없습니다. terraform apply를 먼저 실행하세요."
    echo "   또는 수동으로 지정: S3_BUCKET=버킷이름 bash build_layer.sh"
    exit 1
fi

S3_KEY="layers/xgboost_layer.zip"

echo "============================================"
echo "  XGBoost Lambda Layer 빌드 (S3 경유)"
echo "  버킷: $S3_BUCKET"
echo "============================================"

# 1. 임시 디렉토리에 패키지 설치
echo ""
echo "[1/5] 패키지 설치 중..."
pip install \
    xgboost==2.0.3 \
    scikit-learn==1.3.2 \
    numpy==1.26.4 \
    scipy==1.11.4 \
    -t "$TEMP_DIR/python" \
    --platform manylinux2014_aarch64 \
    --only-binary=:all: \
    --python-version 3.11 \
    --implementation cp \
    2>/dev/null || \
pip install \
    xgboost==2.0.3 \
    scikit-learn==1.3.2 \
    numpy==1.26.4 \
    scipy==1.11.4 \
    -t "$TEMP_DIR/python" \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.11 \
    --implementation cp

# 2. 불필요한 파일 제거 (용량 대폭 줄이기)
echo ""
echo "[2/5] 불필요한 파일 정리 중..."
find "$TEMP_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$TEMP_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find "$TEMP_DIR" -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
find "$TEMP_DIR" -type d -name "benchmarks" -exec rm -rf {} + 2>/dev/null || true
find "$TEMP_DIR" -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find "$TEMP_DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$TEMP_DIR" -name "*.pyx" -delete 2>/dev/null || true
find "$TEMP_DIR" -name "*.pxd" -delete 2>/dev/null || true
find "$TEMP_DIR" -name "*.c" -delete 2>/dev/null || true
find "$TEMP_DIR" -name "*.h" -delete 2>/dev/null || true
# numpy/scipy 테스트와 문서 제거
rm -rf "$TEMP_DIR/python/numpy/tests" 2>/dev/null || true
rm -rf "$TEMP_DIR/python/numpy/doc" 2>/dev/null || true
rm -rf "$TEMP_DIR/python/numpy/f2py" 2>/dev/null || true
rm -rf "$TEMP_DIR/python/numpy/typing" 2>/dev/null || true
rm -rf "$TEMP_DIR/python/scipy/tests" 2>/dev/null || true
rm -rf "$TEMP_DIR/python/scipy/datasets" 2>/dev/null || true
rm -rf "$TEMP_DIR/python/sklearn/tests" 2>/dev/null || true
rm -rf "$TEMP_DIR/python/sklearn/datasets/data" 2>/dev/null || true
rm -rf "$TEMP_DIR/python/sklearn/datasets/descr" 2>/dev/null || true
rm -rf "$TEMP_DIR/python/sklearn/datasets/images" 2>/dev/null || true
# xgboost 불필요 파일 제거
rm -rf "$TEMP_DIR/python/xgboost/testing" 2>/dev/null || true

# 3. zip 생성
echo ""
echo "[3/5] Layer zip 생성 중..."
mkdir -p "$LAYER_DIR"
cd "$TEMP_DIR"
zip -r9 "$LAYER_DIR/xgboost_layer.zip" python/ -x "*.pyc" > /dev/null

LAYER_SIZE=$(du -h "$LAYER_DIR/xgboost_layer.zip" | cut -f1)
echo "  로컬 zip 크기: $LAYER_SIZE"

# 4. S3에 업로드
echo ""
echo "[4/5] S3에 업로드 중..."
aws s3 cp "$LAYER_DIR/xgboost_layer.zip" "s3://$S3_BUCKET/$S3_KEY"
echo "  업로드 완료: s3://$S3_BUCKET/$S3_KEY"

# 5. 정리
rm -rf "$TEMP_DIR"

echo ""
echo "[5/5] 완료!"
echo ""
echo "============================================"
echo "  빌드 & 업로드 완료!"
echo "  S3: s3://$S3_BUCKET/$S3_KEY"
echo "  크기: $LAYER_SIZE"
echo "============================================"
echo ""
echo "  다음 단계:"
echo "  cd $PROJECT_DIR && terraform apply"
echo "============================================"
