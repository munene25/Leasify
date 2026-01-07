from rest_framework.exceptions import ValidationError
from users.models import User
from .validators import UserFieldValidatorMixin


class UserPasswordMixin:
    def _check_current_password(self, *, user: User, current_password):
        """Takes a 'current_password'"""
        if not user.check_password(current_password):
            err = "Current password is incorrect"
            raise ValidationError({"current_password": [err]})

    def _check_passwords_match(self, **kwargs):
        """Requires either 'new_password' only or 'new_password' and 'confirm_password' combination"""
        new_password = kwargs.get("new_password")
        confirm_password = kwargs.get("confirm_password")
        if confirm_password and confirm_password != new_password:
            err = "Passwords do not match"
            raise ValidationError({"new_password": [err], "confirm_password": [err]})