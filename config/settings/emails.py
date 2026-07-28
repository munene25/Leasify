from config.env import env
from enum import Enum

STRATEGY = env.str("EMAIL_SENDING_STRATEGY", default="local")
SERVER_EMAIL = "server@example.com"

ADMINS = [tuple(admin.split(":", 1)) for admin in env.list("ADMINS")]

if STRATEGY == "local":
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

elif STRATEGY == "thirdparty":
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

    EMAIL_HOST = env.str("EMAIL_HOST")
    EMAIL_PORT = env.int("EMAIL_HOST_PORT")
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS")
    EMAIL_HOST_USER = env.str("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD")

ADMINS = env.list("ADMINS", ["edmune25@gmail.com"])
