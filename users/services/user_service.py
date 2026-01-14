from users.models import User
from django.db import transaction
from users.selectors import user_get_locked
from users.mixins import UserPasswordMixin
from rest_framework.exceptions import ValidationError
from django.utils import timezone


class UserService(UserPasswordMixin): 
    def __init__(self, user_id: int|None = None):
        self.user_id = user_id
        self.EDITABLE_FIELDS = {'email', 'username', 'first_name', 'last_name', 'verified'}
        self.PASSWORD_SENSITIVE_FIELDS = {'email', 'username'}

    def user_get_locked(self):
        if not self.user_id:
            raise AttributeError("User Id not provided")
        return user_get_locked(self.user_id)

    def change_email(self, *, user: User, password: str, email: str):
        self._check_current_password(user=user, current_password=password)
        if user.next_email_change is not None:
            err = f"Next available change is '{user.next_email_change}'"
            raise ValidationError({"email": [err]})
        # Update email and revoke verification
        user.email = email
        user.verified = False
        user.last_email_change = timezone.now()
        user.full_clean()
        user.save(update_fields=["email", "last_email_change", "verified"])
        return user

    def change_username(self, *, user: User, password: str, username: str):
        self._check_current_password(user=user, current_password=password)
        if user.next_username_change is not None:
            err = f"Next available change is '{user.next_username_change}'"
            raise ValidationError({"username": [err]})     
        # Update username and last change
        user.username = username
        user.last_username_change = timezone.now()
        user.full_clean()
        user.save(update_fields=["username", "last_username_change"])
        return user
    
    
    @transaction.atomic
    def create(
        self, 
        *,
        username: str,
        password: str,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        notify: bool = True
    )-> User: 
        user = User(
            username = username,
            email = email,
            first_name = first_name,
            _raw_password = password, # required in clean
            verified = False,
            last_name = last_name,
        )
        user.set_password(password)
        user.full_clean()
        user.save()
        if notify:
            # notify the user via email
            # Email class not yet created
            raise NotImplementedError
        return user
    
    @transaction.atomic
    def update(self, **kwargs):
        user = self.user_get_locked()
        update_fields = {
            k: v
            for k, v in kwargs.items()
            if k in self.EDITABLE_FIELDS and getattr(user, k) != v
        }
        
        # Short circuit
        if not update_fields:
            return user 
        
        password = None
        if self.PASSWORD_SENSITIVE_FIELDS & set(update_fields.keys()):
            # Ensure password is provided for email and username change    
            password = kwargs.get("current_password", None)
            if password is None:
                raise ValidationError({"current_password": ["Current password required."]})  
            if "email" in update_fields:
                email = update_fields.pop("email")
                user = self.change_email(user=user, password=password, email=email)       
            if "username" in update_fields:
                username = update_fields.pop("username")
                user = self.change_username(user=user, password=password, username=username)            

        if update_fields:
            for field, value in update_fields.items():
                setattr(user, field, value)
            user.full_clean()
            user.save(update_fields=list(update_fields.keys())) 
        return user

    @transaction.atomic
    def change_password(self, new_password: str, confirm_password: str, current_password: str|None = None) -> User:
        user = self.user_get_locked()
        if current_password:
            self._check_current_password(user=user, current_password=current_password)
        self._check_passwords_match(confirm_password, new_password)
        setattr(user, "_raw_password", new_password)
        user.set_password(new_password)
        user.full_clean()
        user.save()

        return user
        