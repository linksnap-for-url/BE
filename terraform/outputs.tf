output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = module.apigateway.api_endpoint
}

output "urls_table_name" {
  description = "DynamoDB urls table name"
  value       = module.dynamodb.urls_table_name
}

output "stats_table_name" {
  description = "DynamoDB stats table name"
  value       = module.dynamodb.stats_table_name
}
