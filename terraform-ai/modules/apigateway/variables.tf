variable "project_name" {
  description = "프로젝트 이름"
  type        = string
}

variable "environment" {
  description = "환경 (dev, prod)"
  type        = string
}

variable "lambda_invoke_arn" {
  description = "Lambda 호출 ARN"
  type        = string
}

variable "lambda_function_name" {
  description = "Lambda 함수 이름"
  type        = string
}
