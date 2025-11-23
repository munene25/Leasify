from phonenumber_field.phonenumber import PhoneNumber
from rest_framework.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from users.models import User


class UserFieldValidatorMixin:
    def _validate_uniqueness(self, **kwargs):
        errors = {}
        for field, value in kwargs.items():
            if User.objects.filter(**{field: value}).exists():
                errors[field] = [
                    f"{field.replace("_", " ").capitalize()} is not available"
                ]
        if errors:
            raise ValidationError(errors)
        else:
            print("passed_validation")

    def _validate_username_length(self, *, username):
        try:
            MinLengthValidator(limit_value=4, message="username too short")(username)
        except ValidationError as e:
            raise ValidationError({"username": [e]})

    def _validate_password_format(self, *, password, user):
        try:
            validate_password(password, user)
        except DjangoValidationError as exc:
            raise ValidationError({"password": exc.messages})

    def _validate_phone_number_format(self, *, phone_number):
        if isinstance(phone_number, str):
            phone_number = PhoneNumber.from_string(phone_number, "KE")
            if not phone_number.is_valid():
                err = f"Invalid phone number format '{phone_number}'"
                raise ValidationError({"phone_number": [err]})
            self.phone_number = phone_number.as_e164
        if not isinstance(phone_number, PhoneNumber):
            err = f"Invalid phone number format. Requires string or PhoneNumber"
            raise ValidationError({"phone_number": [err]})
