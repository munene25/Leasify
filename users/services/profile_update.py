from users.models import User
from django.db import transaction
from django.db import transaction
from users.models import User
from .account_update import account_update
from .user_update import user_update

@transaction.atomic
def profile_update(_user: User,  **kwargs):
    user = user_update(user=_user, **kwargs)
    acc = getattr(user, "account")
    account = account_update(acc, **kwargs)
    return user, account



