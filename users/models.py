from __future__ import annotations
from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.core.validators import MinLengthValidator, RegexValidator
from django.contrib.auth.models import AbstractUser
from common.models import BaseModel
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from phonenumber_field.modelfields import PhoneNumberField
from phonenumbers import parse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


def phone_number_validator(phone_nubmer):
    if parse(phone_nubmer).country_code != 254:
        raise ValidationError({"phone_number": f"Invalid country code! [{phone_nubmer =}]"}) 


class User(BaseModel, AbstractUser):
    username = None
    first_name = models.CharField(
        "first name",
        max_length=30,
        blank=False,
        validators=[
            RegexValidator(
                regex=r"^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$",
                message="Enter a valid name. Letters, spaces, hyphens, and apostrophes only.",
            ),
            MinLengthValidator(2),
        ],
    )
    last_name = models.CharField(
        "last name",
        max_length=30,
        blank=False,
        validators=[
            RegexValidator(
                regex=r"^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$",
                message="Enter a valid name. Letters, spaces, hyphens, and apostrophes only.",
            ),
            MinLengthValidator(2),
        ],
    )
    email = models.EmailField(unique=True, blank=False)
    verified = models.BooleanField(default=False)
    last_email_change = models.DateTimeField(null=True, blank=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    account: Account

    def clean(self):
        """Properly attatch password requirement messages to the error message"""
        super().clean()
        password = getattr(self, "_raw_password", None)
        if password is not None:
            try:
                validate_password(password, self)
            except DjangoValidationError as exc:
                raise ValidationError({"password": exc.messages})

    def check_password(self, current_password) -> None:
        """Wrapper for check_password with an exception"""
        if not super().check_password(current_password):
            err = "Current password is incorrect"
            raise ValidationError({"current_password": [err]})

    @property
    def next_email_change(self) -> None | datetime:
        if self.last_email_change:
            cooldown = timedelta(days=30)
            next_change_time = self.last_email_change + cooldown
            if next_change_time > timezone.now():
                return timezone.localtime(next_change_time)
        return None

    @property
    def full_name(self) -> str:
        return self.get_full_name()

    @property
    def roles(self) -> list:
        return list(self.groups.values_list("name", flat=True))


# Account Model
class Account(BaseModel):
    """Extra information on the user: Requires phone number field"""

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = PhoneNumberField(
        unique=True,
        null=True,
        blank=True,
        validators=[phone_number_validator],
        error_messages={
            "unique": ("A user with that phone_number already exists."),
        },
    )
    bio = models.TextField(null=True, blank=True, max_length=300)
    backup_email = models.EmailField(null=True, blank=True)
    can_receive_emails = models.BooleanField(default=True)
