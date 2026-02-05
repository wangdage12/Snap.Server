from flask import Flask
from app.config import Config
from app.extensions import init_mongo

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    init_mongo(Config.MONGO_URI, Config.ISTEST_MODE)

    # 注册蓝图
    from routes.announcement import announcement_bp
    from routes.auth import auth_bp
    from routes.gacha_log import gacha_log_bp
    from routes.web_api import web_api_bp
    from routes.misc import misc_bp
    from routes.download_resource import download_resource_bp

    app.register_blueprint(announcement_bp, url_prefix="/Announcement")
    app.register_blueprint(auth_bp)
    app.register_blueprint(gacha_log_bp)
    app.register_blueprint(web_api_bp)
    app.register_blueprint(misc_bp)
    app.register_blueprint(download_resource_bp)

    # CORS
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    return app
