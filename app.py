from app.init import create_app
from app.config_loader import config_loader

# 创建应用实例
app = create_app()

if __name__ == '__main__':
    app.run(
        host=config_loader.SERVER_HOST,
        port=config_loader.SERVER_PORT,
        debug=config_loader.SERVER_DEBUG
    )