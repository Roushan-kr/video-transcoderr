from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    REGION_NAME: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    S3_BUCKET_NAME: str = "" # from docker env variable
    S3_KEY : str = ""        # from docker env variable
    AWS_S3_UPLOAD_BUCKET: str = "" 
secret_keys = Settings()