from typing import Any

from django.core.validators import RegexValidator, MinLengthValidator
from rest_framework import serializers
from django.db import models


class NameFieldValidator(RegexValidator):
    regex = r"^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$"
    message = "Enter a valid name. Letters, spaces, hyphens, and apostrophes only."


class NameModelField(models.CharField):
    """
    A custom CharField for user names that includes validation for common name characters and a minimum length.
    """

    def __init__(self, **kwargs):
        kwargs["max_length"] = 30
        kwargs["validators"] = [NameFieldValidator(), MinLengthValidator(2)]
        super().__init__(**kwargs)


class NameSerializerField(serializers.CharField):
    """
    A custom CharField for user names that includes validation for common name characters and a minimum length.
    """

    def __init__(self, **kwargs):
        kwargs["max_length"] = 30
        kwargs["validators"] = [NameFieldValidator(), MinLengthValidator(2)]
        super().__init__(**kwargs)


class PhoneNumberValidator(RegexValidator):
    regex = r"^\+254\d{9}$"
    message = "Phone number must be in the format +254XXXXXXXXX"

def phone_number_parse(value: str) -> str: 
    """Helper function to normalize and format phone numbers."""
    value = value.replace(" ", "").replace("-", "")
    if value.startswith("0"):
        value = "+254" + value[1:]
    elif value.startswith("254"):
        value = "+" + value
    return value

class PhoneNumberModelField(models.CharField):
    """
    A custom model CharField for phone numbers with validation.
    """

    def __init__(self, **kwargs):
        kwargs["max_length"] = 13
        kwargs["validators"] = [PhoneNumberValidator()]
        kwargs["error_messages"] = {
            "invalid": "Phone number must be in the format +254XXXXXXXXX",
        }
        super().__init__(**kwargs)

    def to_python(self, value: Any) -> Any:
        value = phone_number_parse(value) if isinstance(value, str) else value
        return super().to_python(value)

class PhoneNumberSerializerField(serializers.CharField):
    """
    A custom CharField for phone numbers.
    """

    def __init__(self, **kwargs):
        kwargs["max_length"] = 13
        kwargs["validators"] = [PhoneNumberValidator()]
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        value = phone_number_parse(data) if isinstance(data, str) else data
        return super().to_internal_value(value)
