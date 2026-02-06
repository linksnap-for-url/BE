variable "project_name" {
  description = "프로젝트 이름"
  type        = string
}

variable "environment" {
  description = "환경 (dev, prod)"
  type        = string
}

variable "s3_bucket_arn" {
  description = "S3 버킷 ARN"
  type        = string
}

variable "urls_table_arn" {
  description = "URL DynamoDB 테이블 ARN"
  type        = string
}

variable "stats_table_arn" {
  description = "Stats DynamoDB 테이블 ARN"
  type        = string
}
