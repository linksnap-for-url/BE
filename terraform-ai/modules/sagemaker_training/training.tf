# SageMaker Training Job은 Python 스크립트 (scripts/train_model.py)로 실행

# 학습 완료 후 모델 등록 (모델 경로가 있을 때만)
resource "aws_sagemaker_model" "conversion_model" {
  count = var.deploy_endpoint && var.model_artifact_path != "" ? 1 : 0

  name               = "${var.project_name}-conversion-model-${var.environment}"
  execution_role_arn = var.sagemaker_role_arn

  primary_container {
    image          = "366743142698.dkr.ecr.ap-northeast-2.amazonaws.com/sagemaker-xgboost:1.5-1"
    model_data_url = var.model_artifact_path
    mode           = "SingleModel"
  }

  tags = {
    Name = "${var.project_name}-conversion-model"
  }
}
