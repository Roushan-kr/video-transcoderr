from typing import List
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    REGION_NAME: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_ENDPOINT_URL: str = ""

    AWS_SQS_RAWVIDEO_QUEUE_URL: str = ""
    AWS_ECS_CLUSTER_NAME: str = "video-transcoder-cluster"
    AWS_TASK_DEFINITION: str = "video-transcoder-task"
    AWS_CONTAINER_NAME: str = "video-transcoder"
    AWS_SUBNET_IDS: str = ""  # Comma-separated subnets
    AWS_SECURITY_GROUP_IDS: str = ""  # Comma-separated security groups

    # Pass-through configs to transcoder container
    BACKEND_WEBHOOK_URL: str = "http://backend:8000"
    INTERNAL_API_SECRET: str = "transcoder-internal-secret-token-123"
    PROCESSED_BUCKET_NAME: str = "video-transcoder-processed-bucket"
    CLOUDFRONT_DOMAIN: str = ""

    # Flag for local demonstration without AWS ECS
    LOCAL_DISPATCH_MODE: bool = False


secret_keys = Settings()