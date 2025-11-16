from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class SecretKeys(BaseSettings):
    COGNITO_CLIENT_SEC: str = ""
    COGNITO_CLIENT_ID: str = ""
    REGION_NAME: str = ""
    DATABASE_URL: str = ""

# Create an instance to access the settings
secret_keys = SecretKeys()
    
    