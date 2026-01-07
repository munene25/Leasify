from ..mixins import UserPasswordMixin, UserFieldValidatorMixin
from users.selectors import user_get_by_id
from django.db import transaction
from rest_framework.exceptions import ValidationError


class UserUpdateService(UserPasswordMixin, UserFieldValidatorMixin):
    def __init__(self, *, user_id: int, **kwargs) -> None:
        self.user_id = user_id
        self.email = kwargs.get("email")
        self.username = kwargs.get("username")
        self.phone_number = kwargs.get("phone_number")
        self.first_name = kwargs.get("first_name")
        self.current_password = kwargs.get("current_password")
        self.new_password = kwargs.get("new_password")
        self.confirm_password = kwargs.get("confirm_password")
        self.last_name = kwargs.get("last_name")
        self.bio = kwargs.get("bio")
        self.verified = kwargs.get("verified")
        self.requested_fields = [k for k, v in kwargs.items() if v is not None]

    extra_fields = ("current_password", "new_password", "confirm_password")
    password_sensitive_fields = ("email", "username", "new_password")

    def _get_user(self):
        self.user = user_get_by_id(user_id=self.user_id)

    def _split_fields(self):
        self.extra_fields = [f for f in self.requested_fields if f in self.extra_fields]
        self.update_fields = [
            f
            for f in self.requested_fields
            if hasattr(self.user, f) and getattr(self.user, f) != getattr(self, f)
        ]

    def _require_current_password(self):
        if "current_password" not in self.extra_fields:
            raise ValidationError({"current_password": ["Current password required."]})

    def _update_phone_number(self):
        self._validate_phone_number_format(self.phone_number)
        self._validate_uniqueness(phone_number=self.phone_number)
        self.user.phone_number = self.phone_number

    def _update_email(self):
        if self.user.next_email_change is not None:
            err = f"Next available change is '{self.user.next_email_change}'"
            raise ValidationError({"email": [err]})
        self._validate_uniqueness(email=self.email)
        if "verified" not in self.update_fields:
            self.verified = False
            self.update_fields.append("verified")
        self.user.email = self.email

    def _update_username(self):
        if self.user.next_username_change is not None:
            err = f"Next available change is '{self.user.next_username_change}'"
            raise ValidationError({"username": [err]})
        self._validate_username_length(self.username)
        self._validate_uniqueness(username=self.username)
        self.user.username = self.username

    def _update_password(self):
        self._check_passwords_match(
            new_password=self.new_password,
            confirm_password=self.confirm_password,
        )
        self._validate_password_format(user=self.user, password=self.new_password)
        self.user.set_password(self.new_password)
        
    @transaction.atomic
    def update(self):
        self._get_user()
        self._split_fields()

        if set(self.password_sensitive_fields) & set(self.update_fields):
            self._require_current_password()
            self._check_current_password(
                user=self.user, current_password=self.current_password
            )


        update_map = {
            "email": self._update_email,
            "username": self._update_username,
            "phone_number": self._update_phone_number,
        }

        for field, func in update_map.items():
            if field in self.update_fields:
                func()

        if "new_password" in self.extra_fields:
            self._update_password()
            self.update_fields.append("password")

        for field in ("first_name", "last_name", "verified", "bio"):
            if field in self.update_fields:
                setattr(self.user, field, getattr(self, field))

        self.user.save(update_fields=self.update_fields)
        return self.user
