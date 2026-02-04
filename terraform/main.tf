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
      Project     = "url-shortener"
      ManagedBy   = "terraform"
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



