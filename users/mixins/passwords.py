from rest_framework.exceptions import ValidationError
from users.models import User

class UserPasswordMixin:
    def _check_current_password(self, *, user: User, current_password):
        """Takes a 'current_password'"""
        if not user.check_password(current_password):
            err = "Current password is incorrect"
            raise ValidationError({"current_password": [err]})

    def _check_passwords_match(self, pass1, pass2):
        """Requires either 'new_password' only or 'new_password' and 'confirm_password' combination"""
        if pass1 != pass2 :
            err = "Passwords do not match"
            raise ValidationError({"new_password": [err], "confirm_password": [err]})