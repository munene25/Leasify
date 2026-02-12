from users.models import User, Account
from django.db import transaction
from phonenumber_field.phonenumber import PhoneNumber

@transaction.atomic
def account_unsubscribe(account: Account) -> Account:
    account.can_receive_emails = False
    account.save()
    return account

def account_update(account: Account, **kwargs)  -> Account:
    EDITABLE_FIELDS = {"phone_number", "bio", "backup_email"}
    update_fields = {
        k: v
        for k, v in kwargs.items()
        if k in EDITABLE_FIELDS and getattr(account, k) != v
    }
    if not update_fields:
        return account

    for k, v in update_fields.items():
        setattr(account, k, v)
    account.full_clean()
    account.save(update_fields=list(update_fields.keys()))
    return account


def account_create(
    *,
    user: User,
    phone_number: PhoneNumber,
    bio: str | None = None,
    backup_email: str | None = None,
) -> Account:
    """Should be called within a transaction block"""
    backup_email = User.objects.normalize_email(backup_email)
    acc = Account(
        user=user, phone_number=phone_number, bio=bio, backup_email=backup_email
    )
    acc.full_clean()
    acc.save()
    return acc