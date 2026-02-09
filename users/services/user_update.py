from users.models import User
from django.db import transaction
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.utils import timezone

@transaction.atomic
def user_change_password(*, user: User, new_password: str,  current_password: str|None = None, confirm_password: str) -> User:
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


def user_update(user: User, **kwargs):
    EDITABLE_FIELDS = {'email', 'first_name', 'last_name'}
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


@transaction.atomic
def user_delete_or_deactivate(user: User) -> User | None:
    if user.is_superuser:
        raise PermissionDenied()
    if user.tenancy_set.exists(): #type: ignore
        user.is_active = False
        user.save()
        return user
    user.delete()
    return None

