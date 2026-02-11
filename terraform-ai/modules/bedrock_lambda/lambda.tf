# Lambda 함수 코드 압축
data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/builds/ai_insights.zip"
}

# Lambda 함수
resource "aws_lambda_function" "ai_insights" {
  filename         = data.archive_file.lambda.output_path
  function_name    = "${var.project_name}-ai-insights-${var.environment}"
  role             = var.lambda_role_arn
  handler          = "handler.handler"
  source_code_hash = data.archive_file.lambda.output_base64sha256
  runtime          = "python3.11"
  timeout          = 120  # Bedrock 응답 대기 (2분)
  memory_size      = 256

  environment {
    variables = {
      BEDROCK_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"
      URLS_TABLE    = var.urls_table_name
      STATS_TABLE   = var.stats_table_name
    }
  }

  tags = {
    Name = "${var.project_name}-ai-insights-${var.environment}"
  }
}

# CloudWatch 로그 그룹
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.ai_insights.function_name}"
  retention_in_days = 7  # 비용 절감
}
