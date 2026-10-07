variable "aws_region" {
  description = "AWS deployment region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment identifier (e.g. prod, staging, dev)"
  type        = string
  default     = "prod"
}

variable "raw_bucket_name" {
  description = "Globally unique S3 bucket name for raw uploads"
  type        = string
  default     = "video-transcoder-raw-uploads-prod-001"
}

variable "processed_bucket_name" {
  description = "Globally unique S3 bucket name for processed HLS videos"
  type        = string
  default     = "video-transcoder-processed-hls-prod-001"
}
