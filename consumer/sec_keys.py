from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    REGION_NAME: str = ""
    AWS_SQS_RAWVIDEO_QUEUE_URL: str = ""
    AWS_ECS_CLUSTER_NAME: str = ""
    AWS_TASK_DEFINITION: str = ""
secret_keys = Settings()