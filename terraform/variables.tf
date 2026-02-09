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
  default     = "url-shortener"
}

variable "domain_name" {
  description = "커스텀 도메인 이름"
  type        = string
  default     = "shmall.store"
}

# ============================================
# CloudWatch & Discord Alert 설정
# ============================================

variable "discord_webhook_url" {
  description = "Discord Webhook URL for alerts (terraform.tfvars 또는 환경변수로 설정)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "enable_cloudwatch_monitoring" {
  description = "CloudWatch 모니터링 활성화 여부"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch 로그 보존 기간 (일)"
  type        = number
  default     = 14
}

variable "alarm_thresholds" {
  description = "CloudWatch 알람 임계값 설정"
  type = object({
    lambda_error_threshold       = number
    lambda_duration_threshold_ms = number
    api_5xx_error_threshold      = number
    api_4xx_error_threshold      = number
    api_latency_threshold_ms     = number
  })
  default = {
    lambda_error_threshold       = 5    # 5분 내 에러 5회
    lambda_duration_threshold_ms = 5000 # 5초
    api_5xx_error_threshold      = 10   # 5분 내 5XX 10회
    api_4xx_error_threshold      = 50   # 5분 내 4XX 50회
    api_latency_threshold_ms     = 3000 # 3초
  }
}