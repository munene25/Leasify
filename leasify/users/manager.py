from django.contrib.auth.base_user import BaseUserManager



class UserManager(BaseUserManager):
    """"Provide superuser creation and custom email normalization"""

    @classmethod
    def normalize_email(cls, email: str | None) -> str:
        """Cleaner email normalization. Lowercase email values"""

        email = email or ""
        
        return email.strip().lower()

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        """Default User creation"""

        from leasify.users.services import create
        from leasify.users.models import AccountType

        extra_fields.setdefault("phone_number", None)
        extra_fields.setdefault("account_type", AccountType.EMAIL)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("notify", False)
        

        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("verified", False)

        return create.user_create(
            email=email,
            password=password,
            **extra_fields

        )

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        """Creates a superuser with the given email and password."""
  
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("verified", True)

        return self.create_user(email=email, password=password, **extra_fields)
        




