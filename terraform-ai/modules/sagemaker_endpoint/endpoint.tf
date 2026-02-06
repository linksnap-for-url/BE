# Serverless Endpoint 설정 (비용 최적화!)
resource "aws_sagemaker_endpoint_configuration" "serverless" {
  count = var.deploy_endpoint ? 1 : 0
  
  name = "${var.project_name}-endpoint-config-${var.environment}"

  production_variants {
    variant_name           = "AllTraffic"
    model_name             = var.model_name
    
    # Serverless 설정 (사용할 때만 과금!)
    serverless_config {
      max_concurrency         = 5
      memory_size_in_mb       = 2048
    }
  }

  tags = {
    Name = "${var.project_name}-endpoint-config"
  }
}

# Serverless Endpoint 생성
resource "aws_sagemaker_endpoint" "serverless" {
  count = var.deploy_endpoint ? 1 : 0

  name                 = "${var.project_name}-endpoint-${var.environment}"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.serverless[0].name

  tags = {
    Name = "${var.project_name}-endpoint"
  }
}
