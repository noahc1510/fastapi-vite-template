# 让 uvicorn 可通过 `app:api` 入口加载 ASGI 应用
# 等价于：from app.api import app as api
from .api import app as api

from .config import config