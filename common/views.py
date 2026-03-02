import structlog
from typing import override, Type, cast
from rest_framework.views import APIView
from rest_framework.serializers import Serializer
from rest_framework.exceptions import ValidationError


class BaseAPIView(APIView):
    filter_class: Type[Serializer] | None = None
    serializer_class: Type[Serializer] | None = None

    @override
    def perform_authentication(self, request):
        """
        Centralizes setting of the user_id for the whole request.
        Better here coz django-structlog depends on signals ie request-finished. 
        
        Proves important in service and view level logs, now that the actor is automatically attached.
        Throttle and permission class logs will also share the same context
        """
        super().perform_authentication(request)
        structlog.contextvars.bind_contextvars(
            user_id=request.user.pk if request.user.is_authenticated else None,
        )

    def _run_validation(self, serializer_cls: Type[Serializer], *, data: dict, partial: bool = False) -> dict:
        """Run DRF serializer validation and return validated data."""
        serializer = serializer_cls(data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        return cast(dict, serializer.validated_data)

    def validate_filter(self, *, data: dict) -> dict:
        """Validate query parameters using the filter_class serializer."""
        if self.filter_class is None:
            raise ValueError("filter_class not set")
        return self._run_validation(self.filter_class, data=data, partial=True)

    def validate_serializer(self, *, data: dict, partial: bool = False) -> dict:
        """Validate request body data using the serializer_class serializer."""
        if self.serializer_class is None:
            raise ValueError("serializer_class not set")

        validated = self._run_validation(self.serializer_class, data=data, partial=partial)
        if not validated:
            raise ValidationError("Empty values not allowed")
        return validated
