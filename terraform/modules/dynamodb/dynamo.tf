# URL 저장 테이블
resource "aws_dynamodb_table" "urls" {
  name         = "${var.project_name}-urls-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"  
  hash_key     = "short_code"
  attribute {
    name = "short_code"
    type = "S"  # String
  }
}

# 클릭 통계 테이블
resource "aws_dynamodb_table" "stats" {
  name         = "${var.project_name}-stats-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "short_code"       # PK
  range_key    = "clicked_at"       # SK (정렬 키)

  attribute {
    name = "short_code"
    type = "S"
  }

  attribute {
    name = "clicked_at"
    type = "S"
  }
}