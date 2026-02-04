resource "aws_lambda_function" "create_short_url" {
  function_name = "${var.project_name}-create-short-url-${var.environment}"

  runtime = "python3.10"
  handler = "shorten_url.handler"
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
  handler = "redirect.handler"
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

# Lambda 함수 3: URL별 통계 조회
resource "aws_lambda_function" "get_url_stats" {
  function_name = "${var.project_name}-get-url-stats-${var.environment}"

  runtime = "python3.10"
  handler = "get_url_stats.handler"
  role   = var.lambda_role_arn
  timeout = 30

  filename         = "${path.module}/builds/stats.zip"
  source_code_hash = filebase64sha256("${path.module}/builds/stats.zip")

  environment {
    variables = {
      URLS_TABLE  = var.urls_table_name
      STATS_TABLE = var.stats_table_name
    }
  }
}

# Lambda 함수 4: 전체 사이트 통계 조회
resource "aws_lambda_function" "get_site_stats" {
  function_name = "${var.project_name}-get-site-stats-${var.environment}"

  runtime = "python3.10"
  handler = "get_site_stats.handler"
  role   = var.lambda_role_arn
  timeout = 30

  filename         = "${path.module}/builds/stats.zip"
  source_code_hash = filebase64sha256("${path.module}/builds/stats.zip")

  environment {
    variables = {
      URLS_TABLE  = var.urls_table_name
      STATS_TABLE = var.stats_table_name
    }
  }
}