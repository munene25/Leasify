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


class InvalidPeriodError(APIException):
    """
    Raised when a user tries to book an apartment for a period that's already concluded.
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "invalid_period"
    default_detail = "Start date must be before end date and the period must not be in the past."


class ApartmentUnavailableError(APIException):
    """
    Raised when a user tries to book an apartment that has an overlapping lease.
    """

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Apartment is not available for renting"
    default_code = "apartment_unavailable"


class MaxReservationsExceededError(APIException):
    """
    Raised when the number of reservations for an apartment in the past 2 weeks has exceeded the maximum allowed.
    """

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Maximum number of reservations for user has been exceeded for the month."
    default_code = "max_reservations_exceeded"


class MpesaAPIError(APIException):
    """Raised when a payment mpesa api requests fail."""

    status_code = status.HTTP_424_FAILED_DEPENDENCY
    default_detail = "Action could not be completed at this time. Service is unavailable"
    default_code = "payment_failed"
