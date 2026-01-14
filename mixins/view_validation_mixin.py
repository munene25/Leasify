from typing import Any, Dict, cast


class ValidateSerializerMixin:
    """
    Provides a method to validate input using the view's serializer_class
    and return validated_data as a real dict that **works with Pylance**.
    serializer_class defines the input serializer for deserializing input.
    """

    serializer_class = None  # subclasses must set this

    def validate_input(self, *, data, partial: bool = False) -> Dict[str, Any]:
        if self.serializer_class is None:
            raise RuntimeError("serializer_class not set.")

        serializer = self.serializer_class(data=data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Cast validated_data to real dict for type checkers
        return cast(Dict[str, Any], serializer.validated_data)
