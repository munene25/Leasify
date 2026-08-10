import typing

from django.contrib.auth.base_user import BaseUserManager

if typing.TYPE_CHECKING:
    from leasify.users.models import User


class UserManager(BaseUserManager["User"]):
    """"Provide superuser creation and custom email normalization"""

    @classmethod
    def normalize_email(cls, email: str | None) -> str:
        """Cleaner email normalization. Lowercase email values"""

        email = email or ""
        
        return email.strip().lower()

    def create_user(self, email: str, password: str | None = None, **extra_fields) -> "User":
        """Default User creation with default staff and superuser attributes"""

        from leasify.users.services import create
        from leasify.users.models import AccountType

        extra_fields.setdefault("account_type", AccountType.EMAIL)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("notify", False)
        

        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_staff", False)

        return create.user_create(
            email=email,
            password=password,
            **extra_fields

        )

    def create_superuser(self, email: str, password: str | None = None, **extra_fields) -> "User":
        """Creates a superuser with default attributes."""
  
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)

        return self.create_user(email=email, password=password, **extra_fields)
        




