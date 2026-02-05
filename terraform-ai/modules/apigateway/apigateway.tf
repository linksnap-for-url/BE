# HTTP API 생성
resource "aws_apigatewayv2_api" "ai" {
  name          = "${var.project_name}-ai-api-${var.environment}"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type"]
  }
}

# 스테이지
resource "aws_apigatewayv2_stage" "ai" {
  api_id      = aws_apigatewayv2_api.ai.id
  name        = var.environment
  auto_deploy = true
}

# Lambda 연결: POST /insights
resource "aws_apigatewayv2_integration" "ai_insights" {
  api_id             = aws_apigatewayv2_api.ai.id
  integration_type   = "AWS_PROXY"
  integration_uri    = var.lambda_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "ai_insights_post" {
  api_id    = aws_apigatewayv2_api.ai.id
  route_key = "POST /insights"
  target    = "integrations/${aws_apigatewayv2_integration.ai_insights.id}"
}

# GET /insights도 지원 (간편 테스트용)
resource "aws_apigatewayv2_route" "ai_insights_get" {
  api_id    = aws_apigatewayv2_api.ai.id
  route_key = "GET /insights"
  target    = "integrations/${aws_apigatewayv2_integration.ai_insights.id}"
}

# Lambda 호출 권한
resource "aws_lambda_permission" "api_gateway" {
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.ai.execution_arn}/*/*"
}
