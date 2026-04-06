from rest_framework.exceptions import APIException
from rest_framework import status


class EmailUpdateError(APIException):
    """Raised when email updates are attempted before email cooldown elapses"""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "email_cooldown_active"


class UserLinkMalformedError(APIException):
    """
    Raised when uidb64 or token segments in a generated URL 
    cannot be decoded or are structurally invalid.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The provided link is malformed or has expired."
    default_code = "link_malformed"


class RoleAssignmentError(APIException):
    """
    Raised when uidb64 or token segments in a generated URL
    cannot be decoded or are structurally invalid.
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Only one role is allowed per user."
    default_code = "roles_exceeded"
