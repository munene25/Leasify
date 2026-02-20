from structlog import getLogger
from users.models import User, Account
from django.db import transaction
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from phonenumber_field.phonenumber import PhoneNumber
from users.tasks import send_welcome_email
from .accounts import account_create, account_update

logger = getLogger("users.services")

@transaction.atomic
def user_account_create(*, password: str, email: str, phone_number: PhoneNumber, first_name: str | None = None, last_name: str | None = None, notify: bool = True) -> User:
    email = User.objects.normalize_email(email)
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        verified=False,
    )
    setattr(user, "_raw_password", password)
    user.set_password(password)
    user.full_clean()
    user.save()
    account_create(user=user, phone_number=phone_number)
    if notify:
        send_welcome_email.delay(user.pk)  # type: ignore
    logger.info(f"user [{user.email}] created.")
    return user

@transaction.atomic
def user_account_update(user: User, **kwargs) -> tuple[User, Account]:
    mod_user = user_update(user=user, **kwargs)
    account = getattr(user, "account")
    mod_account = account_update(account, **kwargs)
    return mod_user, mod_account

@transaction.atomic
def user_change_password(*, user: User, new_password: str, current_password: str | None = None) -> User:
    if current_password:
        user.check_current_password(current_password)
    setattr(user, "_raw_password", new_password)
    user.set_password(new_password)
    user.full_clean()
    user.save()
    logger.info(f"user password changed")
    # TODO: Implement mail sending to notify user
    # TODO: Invalidate refresh token
    return user


@transaction.atomic
def user_email_verify(user: User) -> User:
    if user.verified:
        return user
    user.verified = True
    user.save()
    logger.info(f"user verified their email")
    # TODO: Implement mail sending to notify user
    return user

@transaction.atomic
def user_delete_or_deactivate(*, user: User) -> User | None:
    """
    Allows deletion or deactivation of account.
    Denies permission an actor(Administrator) deleting or deactivating a super_user or staff member
    """     
    if user.tenancy_set.exists():  # type: ignore
        user.is_active = False
        user.save()
        logger.info(f"user deactivated.")
        return user
    
    user.delete()
    logger.warning(f"user deleted.")
    return None

@transaction.atomic
def user_update(user: User,  **kwargs):        
    EDITABLE_FIELDS = {"email", "first_name", "last_name"}
    update_fields = {
        k: v
        for k, v in kwargs.items()
        if k in EDITABLE_FIELDS and getattr(user, k) != v
    }
    # Short circuit
    if not update_fields:
        return user

    if "email" in update_fields:
        email = update_fields.pop("email")
        password = kwargs.get("current_password", None)
        if password is None:
            raise ValidationError({"current_password": ["Current password required."]})
        user.check_current_password(password)
        if user.next_email_change is not None:
            err = f"Next available email change is '{user.next_email_change}'"
            raise ValidationError({"email": [err]})
        # Update email and revoke verification
        user.email = email
        user.verified = False
        user.last_email_change = timezone.now()
        user.full_clean()
        user.save(update_fields=["email"])
        logger.info(f"email address changed for user [{user}]")

    if update_fields:
        for field, value in update_fields.items():
            setattr(user, field, value)
        user.full_clean()
        fields = list(update_fields.keys())
        user.save(update_fields=fields)
        logger.info(f"user data modified for {user}. fields: {fields}")
        
    return user