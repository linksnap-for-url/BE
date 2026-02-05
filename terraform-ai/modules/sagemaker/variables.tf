variable "project_name" {
  description = "프로젝트 이름"
  type        = string
}

variable "environment" {
  description = "환경 (dev, prod)"
  type        = string
}

variable "sagemaker_role_arn" {
  description = "SageMaker 실행 역할 ARN"
  type        = string
}
