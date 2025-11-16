import json
from sec_keys import secret_keys
import boto3

sqs_client = boto3.client("sqs", region_name=secret_keys.REGION_NAME)
ecs_client = boto3.client("ecs", region_name=secret_keys.REGION_NAME)


def poll_sqs():
    while True:
        response = sqs_client.receive_message(
            QueueUrl=secret_keys.AWS_SQS_RAWVIDEO_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
        )
        for message in response.get("Messages", []):
            # print("Received message:", message)
            message_body = json.loads(message.get("Body"))
            if (
                "Service" in message_body
                and "Event" in message_body
                and message_body.get("Event") == "s3:TestEvent"
            ):
                sqs_client.delete_message(
                    QueueUrl=secret_keys.AWS_SQS_RAWVIDEO_QUEUE_URL,
                    ReceiptHandle=message["ReceiptHandle"],
                )
                continue
            if "Records" in message_body:
                s3_rds = message_body["Records"][0]["s3"]
                bkt_name = s3_rds["bucket"]["name"]
                s3_key = s3_rds["object"]["key"]

                response = ecs_client.run_task(
                    cluster=secret_keys.AWS_ECS_CLUSTER_NAME,
                    launchType="FARGATE",
                    taskDefinition=secret_keys.AWS_TASK_DEFINITION,
                    overrides={
                        "containerOverrides": [
                            {
                                "name": "video-trancoder",
                                "environment": [
                                    {"name": "S3_BUCKET_NAME", "value": bkt_name},
                                    {"name": "S3_KEY", "value": s3_key}
                                ]
                            }
                        ]
                    },
                    networkConfiguration={
                        "awsvpcConfiguration": {
                            "subnets": [
                                "subnet-0ae5ad7a34d5f9902",
                                "subnet-07bd10925c8fc8dae",
                                "subnet-078eb52cfd27c1a07"
                            ],
                            "securityGroups": [
                                "sg-0b6e0aada927bccab"
                            ],
                            "assignPublicIp": "ENABLED"
                        }
                    }
                )
                print("Started ECS task:", response)
                sqs_client.delete_message(
                    QueueUrl=secret_keys.AWS_SQS_RAWVIDEO_QUEUE_URL,
                    ReceiptHandle=message["ReceiptHandle"]
                )

poll_sqs()
