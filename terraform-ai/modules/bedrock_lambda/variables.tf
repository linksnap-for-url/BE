variable "project_name" {
  description = "프로젝트 이름"
  type        = string
}

variable "environment" {
  description = "환경 (dev, prod)"
  type        = string
}

variable "lambda_role_arn" {
  description = "Lambda 실행 역할 ARN"
  type        = string
}

variable "s3_bucket_name" {
  description = "데이터 S3 버킷 이름"
  type        = string
}

variable "urls_table_name" {
  description = "URL DynamoDB 테이블 이름"
  type        = string
  default     = ""
}

variable "stats_table_name" {
  description = "Stats DynamoDB 테이블 이름"
  type        = string
  default     = ""
}
