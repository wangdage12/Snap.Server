from app.init import create_app
from app.config_loader import config_loader
import sentry_sdk

sentry_sdk.init(
    dsn="https://d1cad1d2b442cf8431df3ee4bab925e0@o4507525750521856.ingest.us.sentry.io/4510623668830208",
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
    traces_sample_rate=1.0,
)

# 创建应用实例
app = create_app()

if __name__ == '__main__':
    app.run(
        host=config_loader.SERVER_HOST,
        port=config_loader.SERVER_PORT,
        debug=config_loader.SERVER_DEBUG
    )