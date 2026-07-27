from django.core.cache import cache
from celery.app.control import Control
import celery


def check_db() -> str:
    try:
        from django.db import connection
        connection.ensure_connection()
        return "ok"
    except Exception:
        return "error"

def check_redis() -> str:
    try:
        cache.set("health", "ok", timeout=1)
        return "ok"
    except Exception:
        return "error"

def check_celery() -> str:
    try:
        app = celery.current_app
        result = Control(app).ping(timeout=1)
        return "ok" if result else "error"
    except Exception:
        return "error"