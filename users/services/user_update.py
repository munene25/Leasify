from users.models import User
from django.db import transaction
from rest_framework.exceptions import ValidationError
from django.utils import timezone

def check_passwords_equality(pass1, pass2):
    """Cheks whether 2 passwords match"""
    if pass1 != pass2 :
        err = "Passwords do not match"
        raise ValidationError({"new_password": [err], "confirm_password": [err]})  

def user_change_password(*, user: User, new_password: str, confirm_password: str, current_password: str|None = None) -> User:
    if current_password:
        user.check_current_password(current_password)
    check_passwords_equality(confirm_password, new_password)
    setattr(user, "_raw_password", new_password)
    user.set_password(new_password)

    user.full_clean()
    user.save()
    # TODO: Implement mail sending to notify user
    # TODO: Invalidate issued JWT tokens
    return user
    

@transaction.atomic
def user_update(user: User, **kwargs):
    EDITABLE_FIELDS = {'email', 'first_name', 'last_name', 'verified'}
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
            err = f"Next available change is '{user.next_email_change}'"
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

