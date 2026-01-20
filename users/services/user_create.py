from users.models import User
from django.db import transaction
from phonenumber_field.phonenumber import PhoneNumber
from .account_create import account_create
from users.tasks import send_welcome_email


@transaction.atomic
def user_create(
    *,
    password: str,
    email: str,
    phone_number: PhoneNumber,
    first_name: str | None = None,
    last_name: str | None = None,
    notify: bool = True
)-> User:
    
    # Normalize Email adress
    email = User.objects.normalize_email(email)
    
    user = User(
        email = email,
        first_name = first_name,
        last_name = last_name,
        verified = False,
    )
    setattr(user, "_raw_password", password)
    user.set_password(password)
    user.full_clean()
    user.save()
    account_create(user=user, phone_number=phone_number)

    if notify:
        send_welcome_email.delay(user.pk)
    
   

    return user