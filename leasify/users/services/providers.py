from leasify.users.models import User, Account
from leasify.users.choices import AccountType
from leasify.users.services import utils


def finalize_email(*, user: User, account: Account, kwargs: dict[str, str]) -> None:
    """
    Finalize an email account by setting and validating its password.

    :param user: The user whose password and verification status should be updated.
    :param account: The account associated with the user.
    :param kwargs: Account data containing the required password and optional backup email.
    :raises ValidationError: If the password is missing or invalid.
    """

    utils.require(kwargs, "password")

    user.verified = False
    user.validate_password(kwargs["password"])
    user.set_password(kwargs["password"])

    if backup_email := kwargs.get("backup_email"):
        account.backup_email = User.objects.normalize_email(backup_email)


def finalize_google(*, user: User, account: Account, kwargs: dict[str, str]) -> None:
    """
    Finalize a Google account using its provider ID.

    :param user: The user whose verification status and password should be updated.
    :param account: The account associated with the user.
    :param kwargs: Account data containing the required Google provider ID.
    :raises ValidationError: If the provider ID is missing.
    """

    utils.require(kwargs, "provider_id")

    user.verified = True
    user.set_unusable_password()
    account.provider_id = kwargs["provider_id"]


HANDLERS = {
    AccountType.GOOGLE: finalize_google,
    AccountType.EMAIL: finalize_email,
}
