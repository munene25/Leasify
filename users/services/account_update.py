from users.models import Account
from django.db import transaction


@transaction.atomic
def account_update( account: Account, **kwargs):
    EDITABLE_FIELDS = {"phone_number", "bio", "backup_email"}
    update_fields = {k: v for k, v in kwargs.items() if k in EDITABLE_FIELDS and getattr(account, k) != v}
    if not update_fields:
        return account
    
    for k, v in update_fields.items():
        setattr(account, k, v)
    account.full_clean()
    account.save(update_fields=list(update_fields.keys()))
