from django.contrib.auth.base_user import BaseUserManager



class UserManager(BaseUserManager):
    """"Provide superuser creation and custom email normalization"""

    @classmethod
    def normalize_email(cls, email: str | None) -> str:
        """Cleaner email normalization. Lowercase email values"""

        email = email or ""
        
        return email.strip().lower()
    
    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        """Creates a superuser with the given email and password."""

        from leasify.users.services import user_create
        from leasify.users.models import AccountType

        extra_fields.setdefault("phone_number", None)

        user = user_create(
            email=email,
            password=password,
            first_name=extra_fields['first_name'],
            last_name=extra_fields['last_name'],
            phone_number=extra_fields["phone_number"],
            account_type=AccountType.EMAIL,
            notify=False,
            is_superuser=True,
            is_staff=True,
            verified=True,

        )
        return user




