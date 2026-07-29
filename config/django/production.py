from config.django.base import *
from config.env import env

DATABASES = {
    "default": env.db("DATABASE_URL")
}

REDIS_URL = env.url("REDIS_URL")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_URL}/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
    "sessions": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_URL}/2",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
    "celery": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_URL}/3",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}

SESSION_CACHE_ALIAS = "sessions"

DEBUG = False

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True

CELERY_BROKER_URL = CACHES["celery"]["LOCATION"]

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

ALLOWED_HOSTS = ALLOWED_HOSTS + env.list("ALLOWED_HOSTS")