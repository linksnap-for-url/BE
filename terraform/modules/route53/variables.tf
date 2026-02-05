variable "domain_name" {
  description = "커스텀 도메인 이름"
  type        = string
}

variable "project_name" {
  description = "프로젝트 이름"
  type        = string
}

variable "environment" {
  description = "환경 (dev, prod)"
  type        = string
}

variable "api_id" {
  description = "API Gateway ID"
  type        = string
}

variable "stage_id" {
  description = "API Gateway Stage ID"
  type        = string
}
