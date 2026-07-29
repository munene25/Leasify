from config.django.base import *

CELERY_TASK_ALWAYS_EAGER = True

if env.bool("USE_REVERSE_PROXY", False):
    BASE_NGROK_URL = "morbidity-blaspheme-shifty.ngrok-free.dev"

    ALLOWED_HOSTS.append(BASE_NGROK_URL)
    CSRF_TRUSTED_ORIGINS.append(BASE_NGROK_URL)
    CORS_ALLOWED_ORIGINS.append(BASE_NGROK_URL)

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]


DRF_STANDARDIZED_ERRORS = {"ENABLE_IN_DEBUG_FOR_UNHANDLED_EXCEPTIONS": True}
