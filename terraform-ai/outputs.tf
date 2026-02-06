output "s3_bucket_name" {
  description = "데이터 저장용 S3 버킷 이름"
  value       = module.s3.bucket_name
}

output "sagemaker_notebook_url" {
  description = "SageMaker 노트북 URL"
  value       = var.enable_sagemaker_notebook ? module.sagemaker[0].notebook_url : "노트북 비활성화됨"
}

output "ai_api_endpoint" {
  description = "AI 인사이트 API 엔드포인트"
  value       = module.apigateway.api_endpoint
}

output "lambda_function_name" {
  description = "Bedrock Lambda 함수 이름"
  value       = module.bedrock_lambda.lambda_function_name
}

output "sagemaker_endpoint_name" {
  description = "SageMaker Endpoint 이름"
  value       = var.deploy_endpoint ? module.sagemaker_endpoint.endpoint_name : "Endpoint 비활성화됨"
}

output "sagemaker_role_arn" {
  description = "SageMaker Role ARN (모델 학습 시 필요)"
  value       = module.iam.sagemaker_role_arn
}

# 다음 단계 안내
output "next_steps" {
  description = "다음 단계 안내"
  value       = <<-EOT

    ==========================================
    AI 배포 완료!
    ==========================================

    AI API 사용법:
    curl -X POST ${module.apigateway.api_endpoint} \
      -H "Content-Type: application/json" \
      -d '{"type": "full"}'

    분석 타입:
    - full: 종합 분석
    - traffic: 트래픽 패턴 분석
    - conversion: 전환 분석

   SageMaker 노트북 사용 (선택):
    terraform apply -var="enable_sagemaker_notebook=true"

    모델 학습 시작 (선택):
    1. 데이터 전처리: python scripts/prepare_data.py --bucket ${module.s3.bucket_name}
    2. 학습 시작: terraform apply -var="run_training=true"

    ==========================================
  EOT
}
