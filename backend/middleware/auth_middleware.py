from fastapi import HTTPException, Cookie
import boto3
from sec_keys import secret_keys

cognito_client = boto3.client("cognito-idp", region_name=secret_keys.REGION_NAME)


def _get_user_from_cognito_access_token(
    access_token: str,
) -> dict:
    try:
        response = cognito_client.get_user(AccessToken=access_token)
        print(response)
        return {
            attr["Name"]: attr["Value"] for attr in response["UserAttributes"]
        }
    except cognito_client.exceptions.NotAuthorizedException:
        raise HTTPException(401, "Invalid access token")
    except Exception as e:
        raise HTTPException(400, f"Error retrieving user info: {str(e)}")
    
def get_current_user(
    access_token: str = Cookie(None),
) -> dict:
    if not access_token:
        raise HTTPException(401, "Access token cookie is missing")
    user_info = _get_user_from_cognito_access_token(access_token)
    return user_info


def get_optional_current_user(
    access_token: str = Cookie(None),
) -> dict | None:
    if not access_token:
        return None
    try:
        return _get_user_from_cognito_access_token(access_token)
    except Exception:
        return None