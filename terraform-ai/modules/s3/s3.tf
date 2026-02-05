# 데이터 저장용 S3 버킷
resource "aws_s3_bucket" "data" {
  bucket = "${var.project_name}-data-${var.environment}-${random_string.suffix.result}"

  tags = {
    Name = "${var.project_name}-data-${var.environment}"
  }
}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# 버전 관리 활성화
resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    status = "Enabled"
  }
}

# 퍼블릭 액세스 차단
resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 데이터 폴더 구조 생성
resource "aws_s3_object" "raw_data_folder" {
  bucket = aws_s3_bucket.data.id
  key    = "raw-data/"
}

resource "aws_s3_object" "processed_data_folder" {
  bucket = aws_s3_bucket.data.id
  key    = "processed-data/"
}

resource "aws_s3_object" "models_folder" {
  bucket = aws_s3_bucket.data.id
  key    = "models/"
}
