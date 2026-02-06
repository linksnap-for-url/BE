variable "aws_region" {
  description = "AWS 리전"
  type        = string
  default     = "ap-northeast-2"
}

variable "environment" {
  description = "환경 (dev, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "프로젝트 이름"
  type        = string
  default     = "linksnap-ai"
}

# SageMaker 옵션
variable "enable_sagemaker_notebook" {
  description = "SageMaker 노트북 활성화 (비용 발생)"
  type        = bool
  default     = false
}

variable "deploy_endpoint" {
  description = "SageMaker Endpoint 배포 (비용 발생)"
  type        = bool
  default     = false
}

variable "model_artifact_path" {
  description = "학습된 모델 S3 경로 (학습 완료 후 설정)"
  type        = string
  default     = ""
}
