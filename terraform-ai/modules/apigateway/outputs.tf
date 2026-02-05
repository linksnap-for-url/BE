output "api_endpoint" {
  description = "AI API 엔드포인트"
  value       = "${aws_apigatewayv2_stage.ai.invoke_url}/insights"
}

output "api_id" {
  description = "API Gateway ID"
  value       = aws_apigatewayv2_api.ai.id
}
