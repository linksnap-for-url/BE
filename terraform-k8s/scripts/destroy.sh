#!/bin/bash
set -e

echo "=== K8s 리소스 삭제 ==="
kubectl delete -f k8s/ --ignore-not-found=true 2>/dev/null || true

echo "=== Terraform Destroy ==="
cd "$(dirname "$0")/.."
terraform destroy -auto-approve

echo "=== EKS 클러스터 삭제 완료! ==="
echo "DynamoDB, Lambda, API Gateway 등 기존 서비스는 영향 없음"
