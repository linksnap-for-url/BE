resource "aws_lambda_function" "create_short_url" {
  function_name = "${var.project_name}-create-short-url-${var.environment}"

  runtime = "python3.10"
  handler = "main.handler"
  role   = var.lambda_role_arn
  timeout = 10

  filename         = "${path.module}/builds/create_url.zip"
  source_code_hash = filebase64sha256("${path.module}/builds/create_url.zip")

  environment {
    variables = {
      URLS_TABLE  = var.urls_table_name
      STATS_TABLE = var.stats_table_name
    }
  }
}

resource "aws_lambda_function" "redirect" {
  function_name = "${var.project_name}-redirect-${var.environment}"

  runtime = "python3.10"
  handler = "main.handler"
  role   = var.lambda_role_arn
  timeout = 10

  filename         = "${path.module}/builds/redirect.zip"
  source_code_hash = filebase64sha256("${path.module}/builds/redirect.zip")

  environment {
    variables = {
      URLS_TABLE  = var.urls_table_name
      STATS_TABLE = var.stats_table_name
    }
  }
}