from __future__ import annotations
from datetime import timedelta, datetime

from django.db import models
from django.utils import timezone
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password

from rest_framework.exceptions import ValidationError

from leasify.common.models import BaseModel
from leasify.users.manager import UserManager
from leasify.users.choices import AccountType
from leasify.common.exceptions import PasswordError
from leasify.common.fields import NameModelField, PhoneNumberModelField

EMAIL_COOLDOWN: timedelta = timedelta(days=14)


class User(BaseModel, AbstractBaseUser, PermissionsMixin):
    """Primary User model with email field"""

  
    email = models.EmailField(unique=True, db_index=True, null=False, blank=False)
    verified = models.BooleanField(null=False, blank=False, default=False)
    first_name = NameModelField(verbose_name="First name", null=False, blank=False)
    last_name = NameModelField(verbose_name="Last name", null=False, blank=False)

    last_email_change = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(null=False, blank=False, default=True)
    is_staff = models.BooleanField(null=False, blank=False, default=False)
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    account: Account
    objects: UserManager = UserManager()

    def verify_password(self, password: str) -> None:
        """Raise PasswordError if Password does not match"""
        if not self.check_password(password):
            raise PasswordError()

    def validate_password(self, password: str,):
        """Validate against settings.AUTH_PASSWORD_VALIDATORS"""
        try:
            validate_password(password, self)
        except DjangoValidationError as exc:
            raise ValidationError({"password": exc.messages})

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
        return f"{self.first_name.capitalize()} {self.last_name.capitalize()}"

    @property
    def role(self) -> str:
        """
        Returns the inherent role of the user on the domain.
        Ranges from superuser, or the group they belong to.
        caching the property causes unexpected behavior when changing user roles mid session.
        Defaults to regular.
        """
        group = self.groups.first()
        if self.is_superuser:
            return "superuser"
        elif group:
            return group.name
        else:
            return "regular"


class Account(BaseModel):
    """Extra information on the user"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    type = models.CharField(null=False, blank=False, choices=AccountType.choices)
    provider_id = models.CharField(unique=True, blank=True, null=True)

    phone_number = PhoneNumberModelField(unique=True, null=True, blank=True)
    backup_email = models.EmailField(null=True, blank=True)
    can_receive_emails = models.BooleanField(default=True)

    user_id: int
