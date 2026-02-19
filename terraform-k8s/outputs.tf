output "ecr_repository_url" {
  description = "ECR 리포지토리 URL (Docker push용)"
  value       = module.ecr.repository_url
}

output "cluster_name" {
  description = "EKS 클러스터 이름"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS 클러스터 엔드포인트"
  value       = module.eks.cluster_endpoint
}

output "kubeconfig_command" {
  description = "kubeconfig 설정 명령어"
  value       = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.aws_region}"
}

output "docker_push_commands" {
  description = "Docker 이미지 빌드 & push 명령어"
  value       = <<-EOT
    # 1. ECR 로그인
    aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${module.ecr.repository_url}

    # 2. Docker 빌드
    cd terraform-k8s/app && docker build -t ${module.ecr.repository_url}:latest .

    # 3. ECR Push
    docker push ${module.ecr.repository_url}:latest
  EOT
}

output "deploy_steps" {
  description = "K8s 배포 단계"
  value       = <<-EOT
    # 1. kubeconfig 설정
    aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.aws_region}

    # 2. K8s 리소스 배포
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/deployment.yaml  (IMAGE_PLACEHOLDER를 ECR URL로 교체)
    kubectl apply -f k8s/service.yaml
    kubectl apply -f k8s/ingress.yaml
    kubectl apply -f k8s/hpa.yaml

    # 3. 상태 확인
    kubectl get pods -n linksnap
    kubectl get svc -n linksnap
    kubectl get ingress -n linksnap
  EOT
}
