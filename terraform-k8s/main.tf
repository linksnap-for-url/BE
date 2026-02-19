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
      Project   = var.project_name
      ManagedBy = "terraform-k8s"
    }
  }
}

# ── 기존 DynamoDB 테이블 참조 (terraform/에서 관리) ──
data "aws_dynamodb_table" "urls" {
  name = "url-shortener-urls-${var.environment}"
}

data "aws_dynamodb_table" "stats" {
  name = "url-shortener-stats-${var.environment}"
}

# ── ECR (destroy 해도 이미지 보존 가능하도록 별도 관리 권장) ──
module "ecr" {
  source       = "./modules/ecr"
  project_name = var.project_name
  environment  = var.environment
}

# ── IAM Roles ──
module "iam" {
  source          = "./modules/iam"
  project_name    = var.project_name
  environment     = var.environment
  urls_table_arn  = data.aws_dynamodb_table.urls.arn
  stats_table_arn = data.aws_dynamodb_table.stats.arn
}

# ── VPC ──
module "vpc" {
  source       = "./modules/vpc"
  project_name = var.project_name
  environment  = var.environment
  cluster_name = var.cluster_name
}

# ── EKS Cluster + Node Group ──
module "eks" {
  source             = "./modules/eks"
  cluster_name       = var.cluster_name
  environment        = var.environment
  cluster_role_arn   = module.iam.cluster_role_arn
  node_role_arn      = module.iam.node_role_arn
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids
  node_instance_type = var.node_instance_type
  node_desired_size  = var.node_desired_size
  node_min_size      = var.node_min_size
  node_max_size      = var.node_max_size
}
