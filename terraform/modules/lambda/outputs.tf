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
