from config.django.base import *


DEBUG = False

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# CELERY
CELERY_TASK_ALWAYS_EAGER = True
CELERY_IGNORE_RESULT = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"