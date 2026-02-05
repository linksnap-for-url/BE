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

# S3 버킷 (데이터 저장용)
module "s3" {
  source       = "./modules/s3"
  project_name = var.project_name
  environment  = var.environment
}

# IAM (SageMaker + Bedrock 권한)
module "iam" {
  source       = "./modules/iam"
  project_name = var.project_name
  environment  = var.environment
  s3_bucket_arn = module.s3.bucket_arn
}

# SageMaker 노트북 (데이터 분석/학습용)
module "sagemaker" {
  source              = "./modules/sagemaker"
  project_name        = var.project_name
  environment         = var.environment
  sagemaker_role_arn  = module.iam.sagemaker_role_arn
}

# Bedrock Lambda (AI 인사이트 API)
module "bedrock_lambda" {
  source              = "./modules/bedrock_lambda"
  project_name        = var.project_name
  environment         = var.environment
  lambda_role_arn     = module.iam.lambda_role_arn
  s3_bucket_name      = module.s3.bucket_name
}

# API Gateway (AI API 엔드포인트)
module "apigateway" {
  source                    = "./modules/apigateway"
  project_name              = var.project_name
  environment               = var.environment
  lambda_invoke_arn         = module.bedrock_lambda.lambda_invoke_arn
  lambda_function_name      = module.bedrock_lambda.lambda_function_name
}
