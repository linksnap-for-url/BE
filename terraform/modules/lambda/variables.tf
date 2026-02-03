variable "project_name" {
  description = "project name"
  type        = string
}

variable "environment" {
  description = "environment (dev, prod)"
  type        = string
}

variable "lambda_role_arn" {
  description = "IAM role ARN for Lambda functions"
  type        = string
}

variable "urls_table_name" {
  description = "DynamoDB urls table name"
  type        = string
}

variable "stats_table_name" {
  description = "DynamoDB stats table name"
  type        = string
}
