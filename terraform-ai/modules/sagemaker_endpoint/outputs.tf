output "endpoint_name" {
  description = "SageMaker Endpoint 이름"
  value       = var.deploy_endpoint ? aws_sagemaker_endpoint.serverless[0].name : null
}

output "endpoint_arn" {
  description = "SageMaker Endpoint ARN"
  value       = var.deploy_endpoint ? aws_sagemaker_endpoint.serverless[0].arn : null
}
