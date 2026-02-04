variable "project_name" {
  description = "project name"
  type        = string
}

variable "environment" {
  description = "environment (dev, prod)"
  type        = string
}

variable "create_short_url_invoke_arn" {
  description = "create short url lambda function invoke ARN"
  type        = string
}

variable "create_short_url_function_name" {
  description = "create short url lambda function name"
  type        = string
}

variable "redirect_invoke_arn" {
  description = "redirect lambda function invoke ARN"
  type        = string
}

variable "redirect_function_name" {
  description = "redirect lambda function name"
  type        = string
}

variable "get_url_stats_invoke_arn" {
  description = "get url stats lambda function invoke ARN"
  type        = string
}

variable "get_url_stats_function_name" {
  description = "get url stats lambda function name"
  type        = string
}

variable "get_site_stats_invoke_arn" {
  description = "get site stats lambda function invoke ARN"
  type        = string
}

variable "get_site_stats_function_name" {
  description = "get site stats lambda function name"
  type        = string
}
