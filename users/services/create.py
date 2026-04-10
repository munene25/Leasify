from structlog import getLogger
from django.contrib.auth.models import Group
from django.db import transaction
from common.exceptions import RoleAssignmentError
from users.models import User, Account
from users.tasks import send_welcome_email

logger = getLogger("users.services.create")


@transaction.atomic
def user_account_create(*, password: str, email: str, first_name: str, last_name: str, notify: bool, phone_number: str | None = None) -> User:
    """
    Creates a user and account instance in one transaction.
    Phone number is only required for payment processing and can be omitted during account creation. It can be added later through account update.
    Phone is technically required during regular user signup, enforced via serializer.

    :param password: The user's password
    :type password: str
    :param email: The user's email
    :type email: str
    :param first_name: The user's first name
    :type first_name: str
    :param last_name: The user's last name
    :type last_name: str
    :param notify: Whether to send a welcome email to the user
    :type notify: bool
    :param phone_number: The user's phone number (region KE)
    :type phone_number: str
    
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
    account_create(user=user, phone_number=phone_number)

    if notify == True:
        transaction.on_commit(lambda: send_welcome_email.delay(user.pk))

    logger.info(f"user {user.get_full_name()} [user_id: {user.pk}] created an account")
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


@transaction.atomic
def user_set_role(*, user: User, role: Group, replace: bool = False) -> User:
    """
    Responsible for adding a user to a group.
    Ensures that only one role can be assigned to a user at a time.
    replace flag explicitly requires the caller to acknowledge that an existing role will be replaced if it exists.

    :param user: The user to whom the role will be added.
    :type user: User
    :param role: The role (Group) to be added to the user.
    :type role: Group
    :param replace: If True, allows replacing an existing role.
    :type replace: bool
    :raises RoleAssignmentError: If the user already has a role and replace is False.
    :return: The user with the newly added role.
    :rtype: User
    """
    if replace == False and user.groups.exists():
        raise RoleAssignmentError()
    user.groups.set([role])
    logger.info(f"Roles [role: {role}] set for [user_id: {user.pk}]")
    return user
