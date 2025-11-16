import boto3
from middleware.auth_middleware import get_current_user
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from db.models.user import User
from db.db import get_db
from helper.auth_helper import get_sec_hash
from sec_keys import secret_keys
from pydantic_model.auth_models import (
    ConformSignUpRequest,
    LoginRequest,
    ReqOtpRequest,
    SignUpRequest,
)
from sqlalchemy.orm import Session

router = APIRouter()

cognito_client = boto3.client("cognito-idp", region_name=secret_keys.REGION_NAME)


@router.post("/signup")
def signup(data: SignUpRequest, db: Session = Depends(get_db)):
    try:
        sec_hash = get_sec_hash(
            username=data.email,
            client_Id=secret_keys.COGNITO_CLIENT_ID,
            client_sec=secret_keys.COGNITO_CLIENT_SEC,
        )

        response = cognito_client.sign_up(
            ClientId=secret_keys.COGNITO_CLIENT_ID,
            Username=data.email,
            Password=data.password,
            SecretHash=sec_hash,
            UserAttributes=[
                {"Name": "name", "Value": data.name},
                {"Name": "email", "Value": data.email},
            ],
        )
        
        cognito_sub = response["UserSub"]

        if not cognito_sub:
            raise HTTPException(400, "Cognito user creation failed")

        new_user = User(name=data.name, email=data.email, cognito_sub=cognito_sub)

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "message": "User signed up successfully",
            "user": new_user,
            "Session": response["Session"],
        }
    except Exception as e:
        raise HTTPException(400, f"Error during sign up: {str(e)}")


@router.post("/login")
def login(data: LoginRequest, response: Response):
    try:
        sec_hash = get_sec_hash(
            username=data.email,
            client_Id=secret_keys.COGNITO_CLIENT_ID,
            client_sec=secret_keys.COGNITO_CLIENT_SEC,
        )

        cognito_response = cognito_client.initiate_auth(
            ClientId=secret_keys.COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": data.email,
                "PASSWORD": data.password,
                "SECRET_HASH": sec_hash,
            },
        )

        if not cognito_response.get("AuthenticationResult"):
            raise HTTPException(400, "Login failed")

        access_token = cognito_response["AuthenticationResult"]["AccessToken"]
        rf_token = cognito_response["AuthenticationResult"]["IdToken"]
        
        response.set_cookie(key="rf_token", value=rf_token, httponly=True, secure=True)
        response.set_cookie(
            key="access_token", value=access_token, httponly=True, secure=True
        )

        return {"message": "Login successful"}
    except Exception as e:
        raise HTTPException(400, f"Error during login: {str(e)}")


@router.post("/verify")
def verifyEmail(data: ConformSignUpRequest):
    try:
        sec_hash = get_sec_hash(
            username=data.email,
            client_Id=secret_keys.COGNITO_CLIENT_ID,
            client_sec=secret_keys.COGNITO_CLIENT_SEC,
        )

        response = cognito_client.confirm_sign_up(
            ClientId=secret_keys.COGNITO_CLIENT_ID,
            SecretHash=sec_hash,
            Username=data.email,
            ConfirmationCode=data.code,
        )
        print(response)
        return {"message": "user confirm successfully", "response": response}
    except Exception as e:
        raise HTTPException(400, f"Error during email verification: {str(e)}")


@router.post("/req-otp")
def reqOtp(data: ReqOtpRequest):
    try:
        sec_hash = get_sec_hash(
            username=data.email,
            client_Id=secret_keys.COGNITO_CLIENT_ID,
            client_sec=secret_keys.COGNITO_CLIENT_SEC,
        )

        response = cognito_client.resend_confirmation_code(
            ClientId=secret_keys.COGNITO_CLIENT_ID,
            SecretHash=sec_hash,
            Username=data.email,
        )
        return {"message": "OTP sent successfully"}
    except Exception as e:
        raise HTTPException(400, f"Error during OTP request: {str(e)}")


@router.post("/refresh-token")
def refresh_token(
    rf_token: str = Cookie(None),
    user_cognito_sub: str = Cookie(None),
    response: Response = Response(None),
):
    if not rf_token and not user_cognito_sub:
        raise HTTPException(401, "Refresh token and user ID are missing")

    sec_hash = get_sec_hash(
        username=user_cognito_sub,
        client_Id=secret_keys.COGNITO_CLIENT_ID,
        client_sec=secret_keys.COGNITO_CLIENT_SEC,
    )

    try:
        # Validate and refresh the token using Cognito
        cognito_response = cognito_client.initiate_auth(
            ClientId=secret_keys.COGNITO_CLIENT_ID,
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={"REFRESH_TOKEN": rf_token, "SECRET_HASH": sec_hash}
        )
        print(cognito_response)
        if not cognito_response.get("AuthenticationResult"):
            raise HTTPException(401, "Invalid refresh token")

        new_access_token = cognito_response["AuthenticationResult"]["AccessToken"]
        new_rf_token = cognito_response["AuthenticationResult"]["IdToken"]
        response.set_cookie(
            key="rf_token", value=new_rf_token, httponly=True, secure=True
        )
        response.set_cookie(
            key="access_token", value=new_access_token, httponly=True, secure=True
        )

        return {"message": "Token refreshed successfully"}
    except Exception as e:
        raise HTTPException(400, f"Error during token refresh: {str(e)}")


@router.get("/me")
def protected_me(user= Depends(get_current_user)):
    return {"message": "Access granted", "user": user}