from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class SecretKeys(BaseSettings):
    COGNITO_CLIENT_SEC: str = ""
    COGNITO_CLIENT_ID: str = ""
    REGION_NAME: str = "us-east-1"
    DATABASE_URL: str = "postgresql://postgres:123456@db:5432/mydatabase"
    RAW_S3_BUCKET_NAME: str = "video-transcoder-raw-bucket"
    PROCESSED_S3_BUCKET_NAME: str = "video-transcoder-processed-bucket"
    CLOUDFRONT_DOMAIN: str = ""
    INTERNAL_API_SECRET: str = "transcoder-internal-secret-token-123"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_ENDPOINT_URL: str = ""  # For LocalStack if used

# Create an instance to access the settings
secret_keys = SecretKeys()