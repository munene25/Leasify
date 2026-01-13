from datetime import timedelta, timezone
from django.db import models
from django.contrib.auth.models import AbstractUser
from phonenumber_field.modelfields import PhoneNumberField
from .manager import UserManager
from mixins.full_clean import ModelExceptionMixin


class User(ModelExceptionMixin, AbstractUser):
    email = models.EmailField(unique=True, blank=False)
    phone_number = PhoneNumberField(unique=True, blank=False)
    bio = models.TextField(blank=True, max_length=300)
    verified = models.BooleanField(default=False)
    last_username_change = models.DateTimeField(null=True, blank=True)
    last_email_change = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    @property
    def next_username_change(self):
        if self.last_username_change:
            cooldown = timedelta(days=30)
            next_change_time = self.last_username_change + cooldown
            if next_change_time > timezone.now():
                return next_change_time
        return None

    @property
    def next_email_change(self):
        if self.last_email_change:
            cooldown = timedelta(days=30)
            next_change_time = self.last_email_change + cooldown
            if next_change_time > timezone.now():
                return next_change_time
        return None

    objects = UserManager()

    @property
    def user_roles(self):
        return list(self.groups.values_list("name", flat=True))
