output "model_name" {
  description = "SageMaker 모델 이름"
  value       = var.deploy_endpoint && var.model_artifact_path != "" ? aws_sagemaker_model.conversion_model[0].name : null
}

output "model_arn" {
  description = "SageMaker 모델 ARN"
  value       = var.deploy_endpoint && var.model_artifact_path != "" ? aws_sagemaker_model.conversion_model[0].arn : null
}
