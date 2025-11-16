from pydantic import BaseModel

class SignUpRequest(BaseModel):
    name: str
    email:str
    password: str
    
class LoginRequest(BaseModel):
    email: str
    password: str

class ConformSignUpRequest(BaseModel):
    email: str
    code: str

class ReqOtpRequest(BaseModel):
    email: str