output "nameservers" {
  description = "가비아에 등록할 네임서버 목록"
  value       = aws_route53_zone.main.name_servers
}

output "hosted_zone_id" {
  description = "Route 53 Hosted Zone ID"
  value       = aws_route53_zone.main.zone_id
}

output "certificate_arn" {
  description = "ACM 인증서 ARN"
  value       = aws_acm_certificate.main.arn
}

output "custom_domain_url" {
  description = "커스텀 도메인 URL"
  value       = "https://${var.domain_name}"
}

output "api_gateway_domain_name" {
  description = "API Gateway 도메인 타겟"
  value       = aws_apigatewayv2_domain_name.main.domain_name_configuration[0].target_domain_name
}
