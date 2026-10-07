from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    REGION_NAME: str = "us-east-1"
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_ENDPOINT_URL: str = ""

    # Inputs from ECS / SQS trigger
    S3_BUCKET_NAME: str = ""
    S3_KEY: str = ""
    VIDEO_ID: str = ""

    # Destination storage & CDN
    AWS_S3_UPLOAD_BUCKET: str = ""
    CLOUDFRONT_DOMAIN: str = ""

    # Backend Callback
    BACKEND_WEBHOOK_URL: str = "http://localhost:8000"
    INTERNAL_API_SECRET: str = "transcoder-internal-secret-token-123"


secret_keys = Settings()