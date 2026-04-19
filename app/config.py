from app.config_loader import config_loader

# 使用配置加载器提供兼容的接口
class Config:
    SECRET_KEY = config_loader.SECRET_KEY
    MONGO_URI = config_loader.MONGO_URI
    TIMEZONE = config_loader.TIMEZONE
    ISTEST_MODE = config_loader.ISTEST_MODE
    EMAIL_PROVIDER = config_loader.EMAIL_PROVIDER
    EMAIL_APP_NAME = config_loader.EMAIL_APP_NAME
    EMAIL_OFFICIAL_WEBSITE = config_loader.EMAIL_OFFICIAL_WEBSITE
    EMAIL_SUBJECT = config_loader.EMAIL_SUBJECT
    EMAIL_FROM_EMAIL = config_loader.EMAIL_FROM_EMAIL
    EMAIL_REPLY_TO = config_loader.EMAIL_REPLY_TO
    EMAIL_RESEND_API_KEY = config_loader.EMAIL_RESEND_API_KEY
    VERIFICATION_CODE_EXPIRE_MINUTES = config_loader.VERIFICATION_CODE_EXPIRE_MINUTES
