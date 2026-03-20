from rest_framework.exceptions import APIException
from rest_framework import status
from users.models import EMAIL_COOLDOWN


class EmailUpdateError(APIException):
    """Raised when email updates are attempted before cooldown elapses"""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = f"Email updates are allowed once every {EMAIL_COOLDOWN.days} days"
    default_code = 'unprocessable'
