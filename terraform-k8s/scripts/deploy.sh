#!/bin/bash
set -e

REGION="ap-northeast-2"
CLUSTER_NAME="linksnap-eks-dev"

echo "=== 1. Terraform Apply ==="
cd "$(dirname "$0")/.."
terraform init
terraform apply -auto-approve

ECR_URL=$(terraform output -raw ecr_repository_url)
echo "ECR URL: $ECR_URL"

echo "=== 2. Docker Build & Push ==="
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "$ECR_URL"
cd app
docker build --platform linux/amd64 -t "$ECR_URL:latest" .
docker push "$ECR_URL:latest"
cd ..

echo "=== 3. kubeconfig 설정 ==="
aws eks update-kubeconfig --name $CLUSTER_NAME --region $REGION

echo "=== 4. K8s 리소스 배포 ==="
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml

# deployment.yaml의 IMAGE_PLACEHOLDER를 실제 ECR URL로 교체해서 적용
sed "s|IMAGE_PLACEHOLDER|$ECR_URL:latest|g" k8s/deployment.yaml | kubectl apply -f -

kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

echo "=== 5. 배포 상태 확인 ==="
kubectl get pods -n linksnap
kubectl get svc -n linksnap
kubectl get ingress -n linksnap

echo "=== 배포 완료! ==="
