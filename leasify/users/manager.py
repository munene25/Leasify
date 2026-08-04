from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """"Provide superuser creation and custom email normalization"""

    @classmethod
    def normalize_email(cls, email: str | None) -> str:
        """Cleaner email normalization. Lowercase email values"""

        if not email:
            raise ValueError("Email is not none")
        return email.strip().lower()
    
    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        """Creates a superuser with the given email and password."""

        from leasify.users.services import user_account_create

        extra_fields.setdefault("phone_number", None)

        user = user_account_create(
            email=email,
            password=password,
            first_name=extra_fields['first_name'],
            last_name=extra_fields['first_name'],
            phone_number=extra_fields["phone_number"],
            notify=False,
        )
        user.is_superuser = True
        user.verified = True
        user.save()
        return user




