terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }

}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "url-shortener"
      ManagedBy = "terraform"
    }
  }
}

# API Gateway 모듈
module "apigateway" {
  source       = "./modules/apigateway"
  project_name = var.project_name
  environment  = var.environment

  create_short_url_invoke_arn    = module.lambda.create_short_url_invoke_arn
  create_short_url_function_name = module.lambda.create_short_url_function_name
  redirect_invoke_arn            = module.lambda.redirect_invoke_arn
  redirect_function_name         = module.lambda.redirect_function_name
  get_url_stats_invoke_arn       = module.lambda.get_url_stats_invoke_arn
  get_url_stats_function_name    = module.lambda.get_url_stats_function_name
  get_site_stats_invoke_arn      = module.lambda.get_site_stats_invoke_arn
  get_site_stats_function_name   = module.lambda.get_site_stats_function_name
}


# Lambda 모듈
module "lambda" {
  source           = "./modules/lambda"
  project_name     = var.project_name
  environment      = var.environment
  lambda_role_arn  = module.iam.lambda_role_arn
  urls_table_name  = module.dynamodb.urls_table_name
  stats_table_name = module.dynamodb.stats_table_name
}

# DynamoDB 모듈
module "dynamodb" {
  source       = "./modules/dynamodb"
  project_name = var.project_name
  environment  = var.environment
}

# IAM 모듈
module "iam" {
  source          = "./modules/iam"
  project_name    = var.project_name
  environment     = var.environment
  urls_table_arn  = module.dynamodb.urls_table_arn
  stats_table_arn = module.dynamodb.stats_table_arn
}

# Route 53 + 커스텀 도메인 모듈
module "route53" {
  source       = "./modules/route53"
  domain_name  = var.domain_name
  project_name = var.project_name
  environment  = var.environment
  api_id       = module.apigateway.api_id
  stage_id     = module.apigateway.stage_id
}

# CloudWatch 모니터링 + Discord 알람 모듈
module "cloudwatch" {
  count  = var.enable_cloudwatch_monitoring && var.discord_webhook_url != "" ? 1 : 0
  source = "./modules/cloudwatch"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region

  # 모니터링할 Lambda 함수 목록
  lambda_function_names = [
    module.lambda.create_short_url_function_name,
    module.lambda.redirect_function_name,
    module.lambda.get_url_stats_function_name,
    module.lambda.get_site_stats_function_name
  ]

  # Discord Webhook URL
  discord_webhook_url = var.discord_webhook_url

  # 로그 보존 기간
  log_retention_days = var.log_retention_days

  # 알람 임계값
  alarm_thresholds = var.alarm_thresholds

  # API Gateway 모니터링
  api_gateway_id    = module.apigateway.api_id
  api_gateway_stage = var.environment
}

