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

variable "s3_bucket_name" {
  description = "데이터/모델 저장 S3 버킷"
  type        = string
}

variable "deploy_endpoint" {
  description = "Endpoint 배포 여부"
  type        = bool
  default     = false
}

variable "model_artifact_path" {
  description = "학습된 모델 S3 경로 (학습 완료 후 설정)"
  type        = string
  default     = ""
}
