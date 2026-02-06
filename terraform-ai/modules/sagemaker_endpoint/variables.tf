variable "project_name" {
  description = "프로젝트 이름"
  type        = string
}

variable "environment" {
  description = "환경 (dev, prod)"
  type        = string
}

variable "deploy_endpoint" {
  description = "Endpoint 배포 여부"
  type        = bool
  default     = false
}

variable "model_name" {
  description = "SageMaker 모델 이름"
  type        = string
  default     = ""
}
