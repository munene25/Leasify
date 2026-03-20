from rest_framework.exceptions import APIException
from rest_framework import status


class EmailUpdateError(APIException):
    """Raised when email updates are attempted before cooldown elapses"""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = 'email_cooldown_active'
