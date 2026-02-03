output "urls_table_name" {
  description = "DynamoDB urls table name"
  value       = aws_dynamodb_table.urls.name
}

output "urls_table_arn" {
  description = "DynamoDB urls table ARN"
  value       = aws_dynamodb_table.urls.arn
}

output "stats_table_name" {
  description = "DynamoDB stats table name"
  value       = aws_dynamodb_table.stats.name
}

output "stats_table_arn" {
  description = "DynamoDB stats table ARN"
  value       = aws_dynamodb_table.stats.arn
}
