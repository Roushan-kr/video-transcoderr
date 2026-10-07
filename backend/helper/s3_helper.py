import boto3
from botocore.config import Config
from sec_keys import secret_keys


def get_s3_client():
    kwargs = {
        "region_name": secret_keys.REGION_NAME or "us-east-1",
        "config": Config(signature_version="s3v4")
    }
    if secret_keys.AWS_ACCESS_KEY_ID and secret_keys.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = secret_keys.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = secret_keys.AWS_SECRET_ACCESS_KEY
    if secret_keys.AWS_ENDPOINT_URL:
        kwargs["endpoint_url"] = secret_keys.AWS_ENDPOINT_URL

    return boto3.client("s3", **kwargs)


def generate_presigned_upload_url(
    bucket_name: str,
    object_key: str,
    content_type: str = "video/mp4",
    expires_in: int = 3600,
) -> str:
    """Generate a presigned PUT URL for direct client S3 upload."""
    s3_client = get_s3_client()
    url = s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": bucket_name,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
    )
    return url
