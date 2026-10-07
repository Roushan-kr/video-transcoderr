variable "queue_name" {
  description = "Name for the raw video ingestion SQS queue"
  type        = string
  default     = "video-transcoder-raw-queue"
}

variable "raw_bucket_arn" {
  description = "ARN of the raw S3 bucket allowed to send messages"
  type        = string
}

# Dead Letter Queue
resource "aws_sqs_queue" "dlq" {
  name                      = "${var.queue_name}-dlq"
  message_retention_seconds = 1209600 # 14 days
}

# Primary SQS Queue with DLQ Redrive
resource "aws_sqs_queue" "main" {
  name                       = var.queue_name
  visibility_timeout_seconds = 900 # 15 minutes (long enough for Fargate spin-up and ABR transcode dispatch)
  message_retention_seconds  = 86400

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

# SQS Policy allowing S3 bucket to publish events
resource "aws_sqs_queue_policy" "allow_s3" {
  queue_url = aws_sqs_queue.main.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowS3ToPublish"
        Effect    = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.main.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = var.raw_bucket_arn
          }
        }
      }
    ]
  })
}

output "queue_url" {
  value = aws_sqs_queue.main.id
}

output "queue_arn" {
  value = aws_sqs_queue.main.arn
}

output "dlq_url" {
  value = aws_sqs_queue.dlq.id
}
