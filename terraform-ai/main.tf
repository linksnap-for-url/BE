terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "linksnap-ai"
      ManagedBy = "terraform"
    }
  }
}

# 기존 DynamoDB 테이블 참조 (terraform/에서 생성된 것)
data "aws_dynamodb_table" "urls" {
  name = "url-shortener-urls-${var.environment}"
}

data "aws_dynamodb_table" "stats" {
  name = "url-shortener-stats-${var.environment}"
}

# S3 버킷 (데이터 저장용)
module "s3" {
  source       = "./modules/s3"
  project_name = var.project_name
  environment  = var.environment
}

# IAM (SageMaker + Bedrock + DynamoDB 권한)
module "iam" {
  source          = "./modules/iam"
  project_name    = var.project_name
  environment     = var.environment
  s3_bucket_arn   = module.s3.bucket_arn
  urls_table_arn  = data.aws_dynamodb_table.urls.arn
  stats_table_arn = data.aws_dynamodb_table.stats.arn
}

# SageMaker 노트북 (데이터 분석/학습용) - 선택적
module "sagemaker" {
  count = var.enable_sagemaker_notebook ? 1 : 0

  source              = "./modules/sagemaker"
  project_name        = var.project_name
  environment         = var.environment
  sagemaker_role_arn  = module.iam.sagemaker_role_arn
}

# SageMaker Model (학습은 Python 스크립트로 실행)
module "sagemaker_training" {
  source              = "./modules/sagemaker_training"
  project_name        = var.project_name
  environment         = var.environment
  sagemaker_role_arn  = module.iam.sagemaker_role_arn
  s3_bucket_name      = module.s3.bucket_name
  deploy_endpoint     = var.deploy_endpoint
  model_artifact_path = var.model_artifact_path
}

# SageMaker Endpoint (실시간 추론) - 선택적
module "sagemaker_endpoint" {
  source          = "./modules/sagemaker_endpoint"
  project_name    = var.project_name
  environment     = var.environment
  deploy_endpoint = var.deploy_endpoint
  model_name      = var.deploy_endpoint ? module.sagemaker_training.model_name : ""
}

# Bedrock Lambda (AI 인사이트 API)
module "bedrock_lambda" {
  source              = "./modules/bedrock_lambda"
  project_name        = var.project_name
  environment         = var.environment
  lambda_role_arn     = module.iam.lambda_role_arn
  s3_bucket_name      = module.s3.bucket_name
  urls_table_name     = data.aws_dynamodb_table.urls.name
  stats_table_name    = data.aws_dynamodb_table.stats.name
  sagemaker_endpoint  = var.deploy_endpoint ? module.sagemaker_endpoint.endpoint_name : ""
}

# API Gateway (AI API 엔드포인트)
module "apigateway" {
  source                    = "./modules/apigateway"
  project_name              = var.project_name
  environment               = var.environment
  lambda_invoke_arn         = module.bedrock_lambda.lambda_invoke_arn
  lambda_function_name      = module.bedrock_lambda.lambda_function_name
}
