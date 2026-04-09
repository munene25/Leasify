from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """"
    Hooks the service layer into the user creation process.
    """
    def create_user(self, email: str, password: str | None = None, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        from users.services import user_account_create

        if not password:
            raise ValueError("Password must be provided")
        
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        user = user_account_create(
            email=email,
            password=password,
            first_name=extra_fields['first_name'],
            last_name=extra_fields['first_name'],
            notify=True,
        )
        return user
    
    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            email=email,
            password=password,
            **extra_fields,
        )
        user.is_staff = True
        user.is_superuser = True
        user.verified = True
        user.save()
        return user




