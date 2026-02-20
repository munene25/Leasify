from typing import Type, Any
from rest_framework.serializers import Serializer, ValidationError

def run_validation(s_cls: Type[Serializer], data: dict, partial: bool = False):
    serializer = s_cls(data=data, partial=partial)
    serializer.is_valid(raise_exception=True)
    validate_data = serializer.validated_data
    if not isinstance(validate_data, dict):
        raise ValidationError("Could not validate the data")
    return validate_data

def validate_filter(**kwargs):
    return run_validation(**kwargs)

def validate_serializer(s_cls: Type[Serializer], data: dict, partial: bool = False) -> dict[str, Any]:
    """
    Explicitly validates data against a serializer class.
    Provides context to the serializer and returns validated_data.
    """
    validated_data = run_validation(s_cls, data, partial)
    if not validated_data:
        raise ValidationError("Invalid or missing fields")
    return validated_data
