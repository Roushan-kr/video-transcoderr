
import base64
import hashlib
import hmac


def get_sec_hash (username:str, client_Id: str, client_sec: str):
    message= username + client_Id
    # using hmac(hash based message authentation code) +sha256 
    
    digest = hmac.new(
        client_sec.encode('utf-8'),
        msg = message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    
    return base64.b64encode(digest).decode()