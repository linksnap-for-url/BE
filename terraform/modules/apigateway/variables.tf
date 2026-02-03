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
