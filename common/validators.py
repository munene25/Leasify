from typing import Type, Any
from rest_framework.serializers import Serializer


def validate_serializer(
    s_cls: Type[Serializer], data: dict, partial: bool = False
) -> dict[str, Any]:
    """
    Explicitly validates data against a serializer class.
    Provides context to the serializer and returns validated_data.
    """
    serializer = s_cls(data=data, partial=partial)
    serializer.is_valid(raise_exception=True)

    return (
        serializer.validated_data if isinstance(serializer.validated_data, dict) else {}
    )
