from structlog import getLogger
from django.contrib.auth.models import Group
from django.db import transaction
from common.exceptions import RoleAssignmentError
from users.models import User, Account
from users.tasks import send_welcome_email

logger = getLogger("users.services.create")


@transaction.atomic
def user_account_create(notify: bool=True, **kwargs) -> User:
    """
    Creates a user and account instance in one transaction.

    :param notify: If True, sends a welcome email to the user after account creation.
    :type notify: bool

    :param kwargs:
        email: str,
        first_name: str,
        last_name: str,
        password: str,
        phone_number: str (optional)

    :return: The created user instance
    :rtype: User
    """

    user = user_create(email=kwargs["email"], password=kwargs["password"], first_name=kwargs["first_name"], last_name=kwargs["last_name"])
    account_create(user=user, phone_number=kwargs.get("phone_number"))

    if notify == True:
        transaction.on_commit(lambda: send_welcome_email.delay(user.pk))
    return user


def user_create(*, email: str, first_name: str, last_name: str, password: str) -> User:
    """
    Creates a user instance without an account. This is used for admin user creation via the django admin panel.
    The account will be created via the AccountInline model.

    :param email: The user's email
    :type email: str
    :param first_name: The user's first name
    :type first_name: str
    :param last_name: The user's last name
    :type last_name: str
    :param password: The user's password
    :type password: str

    :return: The created user instance
    :rtype: User
    """
    email = User.objects.normalize_email(email)
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        verified=False,
    )
    user.set_password(password)
    user.full_clean()
    user.save()
    logger.info(f"user {user.get_full_name()} [user_id: {user.pk}] created an account.")
    return user


@transaction.atomic
def account_create(*, user: User, phone_number: str | None = None, bio: str | None = None, backup_email: str | None = None) -> Account:
    """
    Creates an account instance linked to a user one-one-field
    Phone number can be added later on and is not required.

    :param user: User to be used as the related field
    :type user: User
    :param phone_number: Phone number (region KE) for payment processing
    :type phone_number: str
    :param bio: About the user
    :type bio: str | None
    :param backup_email: Optional Backup email for account recovery
    :type backup_email: str | None
    :return: An account object
    :rtype: Account
    """

    if backup_email:
        backup_email = User.objects.normalize_email(backup_email)
    account = Account(user=user, bio=bio, backup_email=backup_email, phone_number=phone_number)
    account.full_clean()
    account.save()
    return account


