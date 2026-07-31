from config.env import env

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str("SECURITY_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DJANGO_DEBUG", True)

# FRONTEND
FRONTEND_URL = env.str("FRONTEND_URL")
FRONTEND_DOMAIN = env.str("FRONTEND_DOMAIN")

# ALLOWED HOSTS
ALLOWED_HOSTS = ["*"]

# Sessions
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_SECURE = False

# CORS
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = ["*"]

# CSRF
CSRF_TRUSTED_ORIGINS = ["*"]
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = False

USE_REVERSE_PROXY = env.str("USE_REVERSE_PROXY")
if USE_REVERSE_PROXY:
    BASE_REVERSE_PROXY_URL=env.str("BASE_REVERSE_PROXY_URL")