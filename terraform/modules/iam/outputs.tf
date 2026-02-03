output "lambda_role_arn" {
  description = "Lambda IAM role ARN"
  value       = aws_iam_role.lambda_role.arn
}

output "lambda_role_name" {
  description = "Lambda IAM role name"
  value       = aws_iam_role.lambda_role.name
}
