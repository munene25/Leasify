from structlog import getLogger
from users.models import User
from django.db import transaction
from rest_framework.exceptions import ValidationError
from django.utils import timezone

logger = getLogger("users.services.emails")

@transaction.atomic
def user_email_verify(user: User) -> User:
    if user.verified:
        return user
    user.verified = True
    user.save(update_fields=["email"])
    logger.info(f"user verified their email")
    # TODO: Implement mail sending to notify user
    return user


@transaction.atomic
def user_email_update(user: User, email: str, password: str) -> User:
    user.check_password(password)

    # Ensure change is available
    if user.next_email_change is not None:
        err = f"Next available email change is '{user.next_email_change}'"
        raise ValidationError({"email": [err]})
    
    # Normalize email first
    user.email = User.objects.normalize_email(email)

    user.verified = False
    user.last_email_change = timezone.now()
    
    user.full_clean()
    user.save(update_fields=["email", "verified", "last_email_change"])

    # ? Update email and revoke verification
    
    logger.info(f"email address changed for user [{user}]")
    return user