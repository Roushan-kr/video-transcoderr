terraform {
  required_version = ">= 1.5.0"

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
      Project     = "video-transcoder"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# 1. Networking (VPC, Subnets, Security Groups)
module "networking" {
  source      = "./modules/networking"
  environment = var.environment
}

# 2. Storage (S3 Raw & Processed Buckets)
module "storage" {
  source                = "./modules/storage"
  raw_bucket_name       = var.raw_bucket_name
  processed_bucket_name = var.processed_bucket_name
  sqs_queue_arn         = module.queue.queue_arn
}

# 3. Queue (SQS Standard Queue + DLQ)
module "queue" {
  source         = "./modules/queue"
  raw_bucket_arn = module.storage.raw_bucket_arn
}

# 4. Compute (ECR, ECS Fargate Cluster, Task Definitions, IAM)
module "compute" {
  source               = "./modules/compute"
  environment          = var.environment
  raw_bucket_arn       = module.storage.raw_bucket_arn
  processed_bucket_arn = module.storage.processed_bucket_arn
  sqs_queue_arn        = module.queue.queue_arn
}

# 5. Identity & Auth (Cognito User Pool)
module "cognito" {
  source = "./modules/cognito"
}

# 6. Content Delivery Network (CloudFront)
module "cdn" {
  source                                = "./modules/cdn"
  processed_bucket_name                 = module.storage.processed_bucket_name
  processed_bucket_regional_domain_name = module.storage.processed_bucket_regional_domain_name
}
