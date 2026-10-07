output "vpc_id" {
  value = module.networking.vpc_id
}

output "subnet_ids" {
  value = module.networking.subnet_ids
}

output "ecs_security_group_id" {
  value = module.networking.ecs_security_group_id
}

output "raw_s3_bucket" {
  value = module.storage.raw_bucket_name
}

output "processed_s3_bucket" {
  value = module.storage.processed_bucket_name
}

output "sqs_queue_url" {
  value = module.queue.queue_url
}

output "sqs_dlq_url" {
  value = module.queue.dlq_url
}

output "ecs_cluster_name" {
  value = module.compute.cluster_name
}

output "transcoder_task_definition_arn" {
  value = module.compute.task_definition_arn
}

output "transcoder_ecr_repository_url" {
  value = module.compute.transcoder_ecr_url
}

output "consumer_ecr_repository_url" {
  value = module.compute.consumer_ecr_url
}

output "cognito_user_pool_id" {
  value = module.cognito.user_pool_id
}

output "cognito_client_id" {
  value = module.cognito.client_id
}

output "cloudfront_domain" {
  value = module.cdn.cloudfront_domain_name
}
