from __future__ import annotations
from datetime import timedelta, datetime
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from common.models import BaseModel
from users.manager import UserManager
from common.fields import NameModelField, PhoneNumberModelField

EMAIL_COOLDOWN: timedelta = timedelta(days=14)


class User(BaseModel, AbstractUser):
    username = None
    first_name = NameModelField(verbose_name="first name")
    last_name = NameModelField(verbose_name="last name")
    email = models.EmailField(unique=True, blank=False, db_index=True)
    verified = models.BooleanField(null=False, default=False)
    last_email_change = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    account: Account
    objects = UserManager()  # type: ignore

    def clean(self):
        """Properly attatch password requirement messages to the error message"""

        password = getattr(self, "_password", None)
        if password is not None:
            try:
                validate_password(password, self)
            except DjangoValidationError as exc:
                raise ValidationError({"password": exc.messages})

    def validate_password(self, password: str) -> None:
        """Wrapper for check_password. Raises exc if passwords do not match"""
        if not self.check_password(password):
            err = "Password is incorrect"
            raise ValidationError({"password": [err]})

    @property
    def next_email_change(self) -> None | datetime:
        """
        Initially localtime was being returned
        Safer to deal with utc timezone throughout
        """
        if self.last_email_change is None:
            return None

        next_change_time = self.last_email_change + EMAIL_COOLDOWN
        if next_change_time > timezone.now():
            return next_change_time

    @property
    def full_name(self) -> str:
        return self.get_full_name()

    @property
    def role(self) -> str:
        """
        Returns the inherent role of the user on the domain.
        Ranges from superuser, or the group they belong to.
        caching the property causes unexpected behavior when changing user roles mid session.
        Defaults to regular.
        ? Instead of user.role better to have user.rank? as an interger?
        """
        group = self.groups.first()
        if self.is_superuser:
            return "superuser"
        elif group:
            return group.name
        else:
            return "regular"


# Account Model
class Account(BaseModel):
    """Extra information on the user"""

    user_id: int
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = PhoneNumberModelField(unique=True, null=True, blank=True)
    bio = models.TextField(null=True, blank=True, max_length=300)
    backup_email = models.EmailField(null=True, blank=True)
    can_receive_emails = models.BooleanField(default=True)
