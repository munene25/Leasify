from phonenumber_field.phonenumber import PhoneNumber
from users.models import User, Account

def account_create(*, user: User, phone_number: PhoneNumber, bio: str|None = None, backup_email: str|None = None):
    """Called within a transaction block"""
    email = User.objects.normalize_email(backup_email)
    acc = Account(
        user=user,
        phone_number=phone_number,
        bio=bio,
        backup_email=email
    )
    acc.full_clean()
    acc.save()
    return acc
