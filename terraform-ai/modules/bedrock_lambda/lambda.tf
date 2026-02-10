# Lambda 함수 코드 압축
data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/builds/ai_insights.zip"
}

# XGBoost Lambda Layer 
resource "aws_lambda_layer_version" "xgboost" {
  s3_bucket   = var.s3_bucket_name
  s3_key      = "layers/xgboost_layer.zip"
  layer_name          = "${var.project_name}-xgboost-layer-${var.environment}"
  compatible_runtimes = ["python3.11"]
  description         = "XGBoost + scikit-learn for ML inference"
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
  memory_size      = 1024 # 모델 로드에 메모리 필요

  layers = [aws_lambda_layer_version.xgboost.arn]

  environment {
    variables = {
      S3_BUCKET          = var.s3_bucket_name
      BEDROCK_MODEL      = "anthropic.claude-3-haiku-20240307-v1:0"
      URLS_TABLE         = var.urls_table_name
      STATS_TABLE        = var.stats_table_name
      SAGEMAKER_ENDPOINT = var.sagemaker_endpoint
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
