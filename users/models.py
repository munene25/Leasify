from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from mixins.model_full_clean_mixin import ModelExceptionMixin
from django.core.validators import MinLengthValidator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError


class User(ModelExceptionMixin, AbstractUser):
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[UnicodeUsernameValidator(), MinLengthValidator(4)],
        error_messages={
            "unique": ("A user with that username already exists."),
        },
    )
    email = models.EmailField(unique=True, blank=False)
    verified = models.BooleanField(default=False)
    last_username_change = models.DateTimeField(null=True, blank=True)
    last_email_change = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"

    def clean(self):
        super().clean()
        if getattr(self, "_raw_password"):
            try:
                validate_password(self.password, self)
            except DjangoValidationError as exc:
                raise ValidationError({"password": exc.messages})


    @property
    def next_username_change(self):
        if self.last_username_change:
            cooldown = timedelta(days=30)
            next_change_time = self.last_username_change + cooldown
            if next_change_time > timezone.now():
                return timezone.localtime(next_change_time)
        return None

    @property
    def next_email_change(self):
        if self.last_email_change:
            cooldown = timedelta(days=30)
            next_change_time = self.last_email_change + cooldown
            if next_change_time > timezone.now():
                return timezone.localtime(next_change_time)
        return None

    @property
    def user_roles(self):
        return list(self.groups.values_list("name", flat=True))
