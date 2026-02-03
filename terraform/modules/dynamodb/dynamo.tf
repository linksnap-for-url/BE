# URL 저장 테이블
resource "aws_dynamodb_table" "urls" {
  name         = "${var.project_name}-urls-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"  
  hash_key     = "urlId"
  attribute {
    name = "urlId"
    type = "S"  # String
  }
}

# 클릭 통계 테이블
resource "aws_dynamodb_table" "stats" {
  name         = "${var.project_name}-stats-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "statsId"       # PK

  attribute {
    name = "statsId"
    type = "S"
  }
}