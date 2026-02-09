from typing import Any

class ValidateSerializerMixin:
    """
    Provides a method to validate input using the view's serializer_class
    and return validated_data
    """
    serializer_class = None

    def validate_input(self, *, data, partial: bool = False) -> dict[str, Any]:
        if self.serializer_class is None:
            raise RuntimeError("serializer_class not set.")

        serializer = self.serializer_class(data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data
