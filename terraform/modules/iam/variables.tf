variable "project_name" {
  description = "project name"
  type        = string
}

variable "environment" {
  description = "environment (dev, prod)"
  type        = string
}

variable "urls_table_arn" {
  description = "DynamoDB urls table ARN"
  type        = string
}

variable "stats_table_arn" {
  description = "DynamoDB stats table ARN"
  type        = string
}
