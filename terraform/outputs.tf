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

# ============================================
# CloudWatch & Discord Alert Outputs
# ============================================

output "cloudwatch_dashboard_url" {
  description = "CloudWatch Dashboard URL"
  value       = var.enable_cloudwatch_monitoring && var.discord_webhook_url != "" ? "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${var.project_name}-dashboard-${var.environment}" : "CloudWatch 모니터링이 비활성화되어 있습니다"
  sensitive   = true
}

output "sns_topic_arn" {
  description = "CloudWatch 알람 SNS Topic ARN"
  value       = var.enable_cloudwatch_monitoring && var.discord_webhook_url != "" ? module.cloudwatch[0].sns_topic_arn : null
  sensitive   = true
}

output "discord_alert_function_name" {
  description = "Discord Alert Lambda 함수 이름"
  value       = var.enable_cloudwatch_monitoring && var.discord_webhook_url != "" ? module.cloudwatch[0].discord_alert_function_name : null
  sensitive   = true
}
