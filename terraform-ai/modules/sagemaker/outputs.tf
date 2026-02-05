output "notebook_name" {
  description = "SageMaker 노트북 인스턴스 이름"
  value       = aws_sagemaker_notebook_instance.main.name
}

output "notebook_url" {
  description = "SageMaker 노트북 URL"
  value       = "https://${aws_sagemaker_notebook_instance.main.name}.notebook.${data.aws_region.current.name}.sagemaker.aws/lab"
}

data "aws_region" "current" {}
