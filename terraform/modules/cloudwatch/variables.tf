variable "project_name" {
  description = "프로젝트 이름"
  type        = string
}

variable "environment" {
  description = "환경 (dev, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS 리전"
  type        = string
}

# Lambda 함수 이름들
variable "lambda_function_names" {
  description = "모니터링할 Lambda 함수 이름 목록"
  type        = list(string)
}

# Discord Webhook URL (민감정보 - terraform.tfvars나 환경변수로 전달)
variable "discord_webhook_url" {
  description = "Discord Webhook URL for alerts"
  type        = string
  sensitive   = true
}

# CloudWatch 로그 보존 기간 (일)
variable "log_retention_days" {
  description = "CloudWatch 로그 보존 기간 (일)"
  type        = number
  default     = 14
}

# 알람 임계값 설정
variable "alarm_thresholds" {
  description = "CloudWatch 알람 임계값 설정"
  type = object({
    lambda_error_threshold       = number # Lambda 에러 횟수
    lambda_duration_threshold_ms = number # Lambda 실행 시간 (밀리초)
    api_5xx_error_threshold      = number # API Gateway 5XX 에러 횟수
    api_4xx_error_threshold      = number # API Gateway 4XX 에러 횟수
    api_latency_threshold_ms     = number # API 응답 지연 시간 (밀리초)
  })
  default = {
    lambda_error_threshold       = 5
    lambda_duration_threshold_ms = 5000
    api_5xx_error_threshold      = 10
    api_4xx_error_threshold      = 50
    api_latency_threshold_ms     = 3000
  }
}

# API Gateway 모니터링 활성화 여부
variable "enable_api_gateway_alarms" {
  description = "API Gateway 알람 활성화 여부"
  type        = bool
  default     = true
}

# API Gateway ID
variable "api_gateway_id" {
  description = "API Gateway ID for monitoring"
  type        = string
  default     = ""
}

variable "api_gateway_stage" {
  description = "API Gateway Stage name"
  type        = string
  default     = ""
}
