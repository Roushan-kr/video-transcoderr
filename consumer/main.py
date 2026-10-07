import os
import json
import time
import logging
import boto3
from botocore.config import Config
from sec_keys import secret_keys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SQSConsumer")

boto_kwargs = {"region_name": secret_keys.REGION_NAME or "us-east-1"}
if secret_keys.AWS_ACCESS_KEY_ID and secret_keys.AWS_SECRET_ACCESS_KEY:
    boto_kwargs["aws_access_key_id"] = secret_keys.AWS_ACCESS_KEY_ID
    boto_kwargs["aws_secret_access_key"] = secret_keys.AWS_SECRET_ACCESS_KEY
if secret_keys.AWS_ENDPOINT_URL:
    boto_kwargs["endpoint_url"] = secret_keys.AWS_ENDPOINT_URL

sqs_client = boto3.client("sqs", **boto_kwargs)
ecs_client = boto3.client("ecs", **boto_kwargs)


def dispatch_ecs_task(bkt_name: str, s3_key: str, video_id: str):
    """
    Launch an on-demand AWS ECS Fargate task with container overrides,
    or execute local handler if in local demo mode.
    """
    if secret_keys.LOCAL_DISPATCH_MODE:
        logger.info(f"[LOCAL MODE] Simulating dispatch for video_id={video_id}, s3://{bkt_name}/{s3_key}")
        return {"mode": "local_mock", "status": "DISPATCHED"}

    subnets = [s.strip() for s in secret_keys.AWS_SUBNET_IDS.split(",") if s.strip()]
    security_groups = [sg.strip() for sg in secret_keys.AWS_SECURITY_GROUP_IDS.split(",") if sg.strip()]

    if not subnets:
        logger.warning("AWS_SUBNET_IDS not configured. Cannot launch ECS task.")
        return None

    environment_overrides = [
        {"name": "S3_BUCKET_NAME", "value": bkt_name},
        {"name": "S3_KEY", "value": s3_key},
        {"name": "VIDEO_ID", "value": video_id},
        {"name": "AWS_S3_UPLOAD_BUCKET", "value": secret_keys.PROCESSED_BUCKET_NAME},
        {"name": "BACKEND_WEBHOOK_URL", "value": secret_keys.BACKEND_WEBHOOK_URL},
        {"name": "INTERNAL_API_SECRET", "value": secret_keys.INTERNAL_API_SECRET},
        {"name": "CLOUDFRONT_DOMAIN", "value": secret_keys.CLOUDFRONT_DOMAIN},
        {"name": "REGION_NAME", "value": secret_keys.REGION_NAME},
    ]

    logger.info(f"Triggering ECS Fargate task for video_id={video_id} on cluster={secret_keys.AWS_ECS_CLUSTER_NAME}...")

    response = ecs_client.run_task(
        cluster=secret_keys.AWS_ECS_CLUSTER_NAME,
        launchType="FARGATE",
        taskDefinition=secret_keys.AWS_TASK_DEFINITION,
        overrides={
            "containerOverrides": [
                {
                    "name": secret_keys.AWS_CONTAINER_NAME,
                    "environment": environment_overrides,
                }
            ]
        },
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": subnets,
                "securityGroups": security_groups,
                "assignPublicIp": "ENABLED",
            }
        },
    )
    logger.info(f"ECS Task started: {response.get('tasks', [{}])[0].get('taskArn', 'Unknown ARN')}")
    return response


def poll_sqs():
    queue_url = secret_keys.AWS_SQS_RAWVIDEO_QUEUE_URL
    if not queue_url:
        logger.warning("AWS_SQS_RAWVIDEO_QUEUE_URL is not set. Consumer daemon will sleep.")
        while True:
            time.sleep(30)

    logger.info(f"Starting SQS long-polling on: {queue_url}")

    while True:
        try:
            response = sqs_client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,
            )
            messages = response.get("Messages", [])
            for message in messages:
                receipt_handle = message["ReceiptHandle"]
                body_str = message.get("Body", "{}")

                # Handle SNS-wrapped SQS message or direct S3 SQS notification
                try:
                    message_body = json.loads(body_str)
                    if "Message" in message_body and isinstance(message_body["Message"], str):
                        # SNS wrapper
                        message_body = json.loads(message_body["Message"])
                except Exception as e:
                    logger.error(f"Error parsing message body: {e}")
                    continue

                # S3 Test Event
                if message_body.get("Event") == "s3:TestEvent":
                    logger.info("Received S3 test event. Deleting from queue.")
                    sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
                    continue

                if "Records" in message_body:
                    for record in message_body["Records"]:
                        s3_info = record.get("s3", {})
                        bkt_name = s3_info.get("bucket", {}).get("name")
                        s3_key = s3_info.get("object", {}).get("key")

                        if not bkt_name or not s3_key:
                            continue

                        # Extract video ID from key e.g. raw/<video_id>/<filename>
                        parts = s3_key.split("/")
                        if len(parts) >= 3 and parts[0] == "raw":
                            video_id = parts[1]
                        else:
                            video_id = os.path.splitext(os.path.basename(s3_key))[0]

                        logger.info(f"Discovered new raw video: bucket={bkt_name}, key={s3_key}, video_id={video_id}")

                        dispatch_result = dispatch_ecs_task(bkt_name, s3_key, video_id)
                        if dispatch_result:
                            sqs_client.delete_message(
                                QueueUrl=queue_url,
                                ReceiptHandle=receipt_handle,
                            )
                            logger.info(f"SQS message {message.get('MessageId')} successfully processed and deleted.")

        except Exception as e:
            logger.error(f"Error in SQS polling loop: {e}")
            time.sleep(5)


if __name__ == "__main__":
    poll_sqs()
