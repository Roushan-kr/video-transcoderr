variable "raw_bucket_name" {
  description = "Unique name for raw video upload bucket"
  type        = string
}

variable "processed_bucket_name" {
  description = "Unique name for processed HLS video bucket"
  type        = string
}

variable "sqs_queue_arn" {
  description = "ARN of SQS queue to send S3 events to"
  type        = string
  default     = ""
}

# Raw Ingestion S3 Bucket
resource "aws_s3_bucket" "raw" {
  bucket        = var.raw_bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_cors_configuration" "raw_cors" {
  bucket = aws_s3_bucket.raw.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST", "GET"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Processed HLS S3 Bucket
resource "aws_s3_bucket" "processed" {
  bucket        = var.processed_bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_cors_configuration" "processed_cors" {
  bucket = aws_s3_bucket.processed.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["Content-Length", "Content-Range", "ETag"]
    max_age_seconds = 3000
  }
}

# S3 Notification to SQS for Raw Uploads
resource "aws_s3_bucket_notification" "bucket_notification" {
  count  = var.sqs_queue_arn != "" ? 1 : 0
  bucket = aws_s3_bucket.raw.id

  queue {
    queue_arn     = var.sqs_queue_arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "raw/"
  }
}

output "raw_bucket_name" {
  value = aws_s3_bucket.raw.id
}

output "raw_bucket_arn" {
  value = aws_s3_bucket.raw.arn
}

output "processed_bucket_name" {
  value = aws_s3_bucket.processed.id
}

output "processed_bucket_arn" {
  value = aws_s3_bucket.processed.arn
}

output "processed_bucket_regional_domain_name" {
  value = aws_s3_bucket.processed.bucket_regional_domain_name
}
