from app.config_loader import config_loader

# 使用配置加载器提供兼容的接口
class Config:
    SECRET_KEY = config_loader.SECRET_KEY
    MONGO_URI = config_loader.MONGO_URI
    TIMEZONE = config_loader.TIMEZONE
    ISTEST_MODE = config_loader.ISTEST_MODE
    EMAIL_APP_NAME = config_loader.EMAIL_APP_NAME
    EMAIL_OFFICIAL_WEBSITE = config_loader.EMAIL_OFFICIAL_WEBSITE
    EMAIL_SUBJECT = config_loader.EMAIL_SUBJECT
    VERIFICATION_CODE_EXPIRE_MINUTES = config_loader.VERIFICATION_CODE_EXPIRE_MINUTES
