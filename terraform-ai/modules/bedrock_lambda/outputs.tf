output "lambda_function_name" {
  description = "Lambda 함수 이름"
  value       = aws_lambda_function.ai_insights.function_name
}

output "lambda_invoke_arn" {
  description = "Lambda 호출 ARN"
  value       = aws_lambda_function.ai_insights.invoke_arn
}

output "lambda_arn" {
  description = "Lambda ARN"
  value       = aws_lambda_function.ai_insights.arn
}
