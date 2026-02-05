output "s3_bucket_name" {
  description = "데이터 저장용 S3 버킷 이름"
  value       = module.s3.bucket_name
}

output "sagemaker_notebook_url" {
  description = "SageMaker 노트북 URL"
  value       = module.sagemaker.notebook_url
}

output "ai_api_endpoint" {
  description = "AI 인사이트 API 엔드포인트"
  value       = module.apigateway.api_endpoint
}

output "lambda_function_name" {
  description = "Bedrock Lambda 함수 이름"
  value       = module.bedrock_lambda.lambda_function_name
}
