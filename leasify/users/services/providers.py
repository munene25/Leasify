from leasify.users.models import User, Account
from leasify.users.choices import AccountType
from leasify.users.services import utils

def finalize_email(*, user: User, account: Account, kwargs: dict[str, str]) -> None:
    """Requires password to be explicitly set"""
    
    utils.require(kwargs, "password")

    user.verified = False
    user.validate_password(kwargs["password"])
    user.set_password(kwargs["password"])

    if (backup_email := kwargs.get("backup_email")):
        account.backup_email = User.objects.normalize_email(backup_email)

def finalize_google(*, user: User, account: Account, kwargs: dict[str, str]) -> None:
    """Set provider id and verified status True"""

    utils.require(kwargs, "provider_id")

    user.verified = True
    user.set_unusable_password()
    account.provider_id = kwargs["provider_id"]


HANDLERS = {
    AccountType.GOOGLE: finalize_google,
    AccountType.EMAIL: finalize_email,
}