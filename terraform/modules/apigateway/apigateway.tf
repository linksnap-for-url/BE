# HTTP API 생성
resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project_name}-api-${var.environment}"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type"]
  }
}

# 스테이지 (dev, prod 등)
resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = var.environment
  auto_deploy = true
}

# Lambda 연결 1: POST /shorten
resource "aws_apigatewayv2_integration" "create_short_url" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "AWS_PROXY"
  integration_uri    = var.create_short_url_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "create_short_url" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /shorten"
  target    = "integrations/${aws_apigatewayv2_integration.create_short_url.id}"
}

# Lambda 연결 2: GET /{shortCode} (리다이렉트)
resource "aws_apigatewayv2_integration" "redirect" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "AWS_PROXY"
  integration_uri    = var.redirect_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "redirect" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /{shortCode}"
  target    = "integrations/${aws_apigatewayv2_integration.redirect.id}"
}

# Lambda 연결 3: GET /stats/{shortCode} (URL별 통계)
resource "aws_apigatewayv2_integration" "get_url_stats" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "AWS_PROXY"
  integration_uri    = var.get_url_stats_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_url_stats" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /stats/{shortCode}"
  target    = "integrations/${aws_apigatewayv2_integration.get_url_stats.id}"
}

# Lambda 연결 4: GET /stats (전체 사이트 통계)
resource "aws_apigatewayv2_integration" "get_site_stats" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "AWS_PROXY"
  integration_uri    = var.get_site_stats_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_site_stats" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /stats"
  target    = "integrations/${aws_apigatewayv2_integration.get_site_stats.id}"
}

# Lambda 호출 권한
resource "aws_lambda_permission" "create_short_url" {
  action        = "lambda:InvokeFunction"
  function_name = var.create_short_url_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "redirect" {
  action        = "lambda:InvokeFunction"
  function_name = var.redirect_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "get_url_stats" {
  action        = "lambda:InvokeFunction"
  function_name = var.get_url_stats_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "get_site_stats" {
  action        = "lambda:InvokeFunction"
  function_name = var.get_site_stats_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}