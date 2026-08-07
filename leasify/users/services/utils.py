from rest_framework.exceptions import ValidationError

def require(kwargs: dict, *fields: str) -> None:
    """A helper function to raise for required fields"""
    errors = {}
    for field in fields:
        if not kwargs.get(field):
            errors[field] = "This field is required"
    if errors:
        raise ValidationError(errors)


