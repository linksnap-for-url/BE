output "create_short_url_function_name" {
  description = "create short url Lambda function name"
  value       = aws_lambda_function.create_short_url.function_name
}

output "create_short_url_invoke_arn" {
  description = "create short url Lambda function invoke ARN"
  value       = aws_lambda_function.create_short_url.invoke_arn
}

output "redirect_function_name" {
  description = "redirect Lambda function name"
  value       = aws_lambda_function.redirect.function_name
}

output "redirect_invoke_arn" {
  description = "redirect Lambda function invoke ARN"
  value       = aws_lambda_function.redirect.invoke_arn
}

output "get_url_stats_function_name" {
  description = "get url stats Lambda function name"
  value       = aws_lambda_function.get_url_stats.function_name
}

output "get_url_stats_invoke_arn" {
  description = "get url stats Lambda function invoke ARN"
  value       = aws_lambda_function.get_url_stats.invoke_arn
}

output "get_site_stats_function_name" {
  description = "get site stats Lambda function name"
  value       = aws_lambda_function.get_site_stats.function_name
}

output "get_site_stats_invoke_arn" {
  description = "get site stats Lambda function invoke ARN"
  value       = aws_lambda_function.get_site_stats.invoke_arn
}
