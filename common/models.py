from django.core.exceptions import  ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.db import models

class BaseModel(models.Model):
    """
    Provide a uniform error message on running full clean on models. Raises
    standard DRF errors by overriding the models original full_clean
    """

    class Meta:
        ordering = ["-created_at"]
        abstract = True
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def full_clean(self, *args, **kwargs) -> None:
        try:
            super().full_clean(*args, **kwargs)
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict)

