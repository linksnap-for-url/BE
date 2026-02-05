output "api_endpoint" {
  description = "API Gateway endpoint URL (기본)"
  value       = module.apigateway.api_endpoint
}

output "custom_domain_url" {
  description = "커스텀 도메인 URL (단축 URL용)"
  value       = module.route53.custom_domain_url
}

output "nameservers" {
  description = "가비아에 등록할 네임서버 목록"
  value       = module.route53.nameservers
}

output "urls_table_name" {
  description = "DynamoDB urls table name"
  value       = module.dynamodb.urls_table_name
}

output "stats_table_name" {
  description = "DynamoDB stats table name"
  value       = module.dynamodb.stats_table_name
}
