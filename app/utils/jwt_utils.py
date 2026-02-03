import jwt
import datetime
from flask import current_app
from app.config_loader import config_loader

def create_token(user_id: str) -> str:
    """
    创建JWT访问令牌，有效期由配置文件中的JWT_EXPIRATION_HOURS决定。
    
    :param user_id: 用户ID
    :return: JWT 访问令牌
    """
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=config_loader.JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm=config_loader.JWT_ALGORITHM)

# 创建刷新token，有效期是访问token的两倍
def create_refresh_token(user_id: str) -> str:
    """
    创建JWT刷新令牌，有效期为访问令牌的两倍。
    
    :param user_id: 用户ID
    :return: JWT 刷新令牌
    """
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=config_loader.JWT_EXPIRATION_HOURS * 2)
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm=config_loader.JWT_ALGORITHM)

def verify_token(token: str)-> str | None:
    """
    验证JWT令牌并返回用户ID，如果无效则返回None。
    
    :param token: JWT令牌字符串
    :type token: str
    :return: 用户ID或None
    :rtype: str | None
    """
    try:
        data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=[config_loader.JWT_ALGORITHM])
        return data["user_id"]
    except:
        return None
