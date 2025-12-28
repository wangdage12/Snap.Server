import json
import os
from zoneinfo import ZoneInfo
from typing import Dict, Any

class ConfigLoader:
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self._config = None
    
    def load_config(self) -> Dict[str, Any]:
        """加载 JSON 配置文件"""
        if self._config is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), self.config_file)
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except FileNotFoundError:
                raise FileNotFoundError(f"配置文件 {config_path} 不存在")
            except json.JSONDecodeError as e:
                raise ValueError(f"配置文件格式错误: {e}")
        
        return self._config
    
    def get(self, key: str, default=None):
        """获取配置值，支持点号分隔的嵌套键"""
        config = self.load_config()
        keys = key.split('.')
        value = config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    @property
    def SECRET_KEY(self) -> str:
        return self.get('SECRET_KEY')
    
    @property
    def MONGO_URI(self) -> str:
        return self.get('MONGO_URI')
    
    @property
    def TIMEZONE(self) -> ZoneInfo:
        timezone_str = self.get('TIMEZONE', 'Asia/Shanghai')
        return ZoneInfo(timezone_str)
    
    @property
    def ISTEST_MODE(self) -> bool:
        return self.get('ISTEST_MODE', False)
    
    @property
    def SERVER_HOST(self) -> str:
        return self.get('SERVER.HOST', '0.0.0.0')
    
    @property
    def SERVER_PORT(self) -> int:
        return self.get('SERVER.PORT', 5222)
    
    @property
    def SERVER_DEBUG(self) -> bool:
        return self.get('SERVER.DEBUG', False)
    
    @property
    def JWT_ALGORITHM(self) -> str:
        return self.get('JWT.ALGORITHM', 'HS256')
    
    @property
    def JWT_EXPIRATION_HOURS(self) -> int:
        return self.get('JWT.EXPIRATION_HOURS', 24)
    
    @property
    def EMAIL_GMAIL_USER(self) -> str:
        return self.get('EMAIL.GMAIL_USER')
    
    @property
    def EMAIL_APP_PASSWORD(self) -> str:
        return self.get('EMAIL.APP_PASSWORD')
    
    @property
    def RSA_PRIVATE_KEY_FILE(self) -> str:
        return self.get('RSA.PRIVATE_KEY_FILE', 'private.pem')
    
    @property
    def RSA_PUBLIC_KEY_FILE(self) -> str:
        return self.get('RSA.PUBLIC_KEY_FILE', 'public.pem')
    
    @property
    def LOGGING_LEVEL(self) -> str:
        return self.get('LOGGING.LEVEL', 'DEBUG')
    
    @property
    def LOGGING_FORMAT(self) -> str:
        return self.get('LOGGING.FORMAT', '%(asctime)s %(name)s %(levelname)s %(message)s')

# 创建全局配置实例
config_loader = ConfigLoader()