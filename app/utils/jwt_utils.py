import jwt
import datetime
from flask import current_app
from app.config_loader import config_loader

def create_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=config_loader.JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm=config_loader.JWT_ALGORITHM)

def verify_token(token):
    try:
        data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=[config_loader.JWT_ALGORITHM])
        return data["user_id"]
    except:
        return None
