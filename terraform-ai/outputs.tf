output "s3_bucket_name" {
  description = "데이터 저장용 S3 버킷 이름"
  value       = module.s3.bucket_name
}

output "ai_api_endpoint" {
  description = "AI 인사이트 API 엔드포인트"
  value       = module.apigateway.api_endpoint
}

output "lambda_function_name" {
  description = "Bedrock Lambda 함수 이름"
  value       = module.bedrock_lambda.lambda_function_name
}

# 다음 단계 안내
output "next_steps" {
  description = "다음 단계 안내"
  value       = <<-EOT

    ==========================================
    AI 배포 완료! (Bedrock Only)
    ==========================================

    AI API 사용법:
    curl -X POST ${module.apigateway.api_endpoint} \
      -H "Content-Type: application/json" \
      -d '{"type": "full"}'

    분석 타입:
    - full: 종합 분석
    - traffic: 트래픽 패턴 분석
    - conversion: 전환 분석

    ==========================================
  EOT
}
