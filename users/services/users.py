import logging
from users.models import User, Account
from django.db import transaction
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from phonenumber_field.phonenumber import PhoneNumber
from users.tasks import send_welcome_email
from .accounts import account_create, account_update

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
    return user

@transaction.atomic
def user_account_update(_user: User, **kwargs) -> tuple[User, Account]:
    user = user_update(user=_user, **kwargs)
    acc = getattr(user, "account")
    account = account_update(acc, **kwargs)
    return user, account

@transaction.atomic
def user_change_password(*, user: User, new_password: str, current_password: str | None = None, confirm_password: str) -> User:
    if current_password:
        user.check_current_password(current_password)
    setattr(user, "_raw_password", new_password)
    user.set_password(new_password)
    user.full_clean()
    user.save()
    # TODO: Implement mail sending to notify user
    # TODO: Invalidate refresh token
    return user


@transaction.atomic
def user_email_verify(user: User):
    if user.verified:
        return user
    user.verified = True
    # TODO: Implement mail sending to notify user
    user.save()

@transaction.atomic
def user_delete_or_deactivate(*, actor: User, target: User) -> User | None:
    if target.is_superuser:
        raise PermissionDenied()
    if user.tenancy_set.exists():  # type: ignore
        target.is_active = False
        target.save()
        return target
    target.delete()
    return None


def user_update(user: User, **kwargs):
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

    if update_fields:
        for field, value in update_fields.items():
            setattr(user, field, value)
        user.full_clean()
        user.save()
    return user