from logging import getLogger
from users.models import User, Account
from django.db import transaction
from phonenumber_field.phonenumber import PhoneNumber

logger = getLogger("users.accounts.services")

@transaction.atomic
def account_unsubscribe(account: Account) -> Account:
    """
    Unsubscribes a user from the mailing list.
    """
    account.can_receive_emails = False
    account.save()
    logger.info(f"User {account.user} has unsubscribed from mailling list")
    return account

def account_update(account: Account, **kwargs)  -> Account:
    """
    Update fields for the account model
    
    :param account: Account instance to update
    :type account: Account
    :param kwargs: phone_number: PhoneNumber, bio: str, backup_email: str 
    :return: Description
    :rtype: Account
    """
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
    updates = list(update_fields.keys())
    account.save(update_fields=updates)
    logger.info(f"User {account.user} has updated fields {updates}")
    return account

@transaction.atomic
def account_create(*, user: User, phone_number: PhoneNumber, bio: str | None = None, backup_email: str | None = None ) -> Account:
    """
    Creates an account instance linked to a user one-one-field
    
    :param user: User to be used as the related field
    :type user: User
    :param phone_number: Phone number (region KE) for payment processing
    :type phone_number: PhoneNumber
    :param bio: About the user
    :type bio: str | None
    :param backup_email: Optional Backup email for account recovery
    :type backup_email: str | None
    :return: An account object
    :rtype: Account
    """
    backup_email = User.objects.normalize_email(backup_email) 
    account = Account(
        user=user, phone_number=phone_number, bio=bio, backup_email=backup_email
    )
    account.full_clean()
    account.save()
    return account