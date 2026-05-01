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

class SemesterEndedError(APIException):
    """
    Raised when a user tries to book an apartment for a semester that's already concluded.
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "invalid_semester"
    default_detail = "Semester has already concluded"


class ApartmentOccupiedError(APIException):
    """
    Raised when a user tries to book an already booked apartment.
    This is in cases where the apartment is marked rentable but occupied at the same time.
    """
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Apartment is already occupied."
    default_code = "apartment_occupied"

class OverpaymentError(APIException):
    """
    Raised when the total amount being paid is more than the rent due for the apartment.
    """
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This payment will result in an overpay."
    default_code = "payment_exceeds_rent"