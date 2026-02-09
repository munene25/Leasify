from django.core.exceptions import  ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError


class ModelExceptionMixin:
    """
    Provide a uniform mixin for models running full clean to raise
    standard DRF errors by overriding the models original full_clean
    """

    def full_clean(self, *args, **kwargs) -> None:
        try:
            super().full_clean(*args, **kwargs)  # type:ignore
        except DjangoValidationError as exc:
            errors = exc.message_dict
            raise DRFValidationError(errors)

