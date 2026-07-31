from config.django.base import *
from config.env import env

DEBUG = False

DATABASES = {
    "default": env.db("DATABASE_URL")
}

REDIS_URL = env.str("REDIS_URL")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}

# CSRF
CSRF_COOKIE_SECURE = True

# SESSIONS
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_COOKIE_SECURE = True

# ALLOWED HOSTS
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# CORS
CORS_ALLOWED_ORIGINS = env.list("FRONTEND_ORIGINS")

# CSRF
CSRF_TRUSTED_ORIGINS  = env.list("FRONTEND_ORIGINS")
CSRF_COOKIE_SECURE = True

# CELERY
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = "django-db"
CELERY_TASK_ALWAYS_EAGER = False

REST_FRAMEWORK["NUM_PROXIES"] = 1