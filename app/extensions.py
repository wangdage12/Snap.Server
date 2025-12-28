import logging
import coloredlogs
import secrets
import string
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from app.config_loader import config_loader

logger = logging.getLogger("app")
coloredlogs.install(level=config_loader.LOGGING_LEVEL, logger=logger, fmt=config_loader.LOGGING_FORMAT)

client = None

def init_mongo(uri: str, test_mode=False):
    global client
    if test_mode:
        logger.info("Running in test mode, skipping MongoDB connection")
        return
    
    client = MongoClient(uri, server_api=ServerApi('1'))

    try:
        client.admin.command('ping')
        logger.info("MongoDB connected successfully")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise

def generate_code(length=6):
    """生成数字验证码"""
    return ''.join(secrets.choice('0123456789') for _ in range(length))

def generate_numeric_id(length=8):
    """生成数字ID"""
    return ''.join(secrets.choice(string.digits) for _ in range(length))
