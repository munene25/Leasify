from structlog import getLogger
from django.contrib.auth.models import Group
from django.db import transaction
from phonenumber_field.phonenumber import PhoneNumber
from common.exceptions import RoleAssignmentError
from users.models import User, Account
from users.tasks import send_welcome_email

logger = getLogger("users.services.create")

@transaction.atomic
def user_account_create(*, password: str, email: str, phone_number: PhoneNumber, first_name:str, last_name: str , notify: bool) -> User:
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

@transaction.atomic
def user_add_role(*, user: User, role: Group)-> User:
    """
        Responsible for adding a user to a group.
        Ensures that only one role can be assigned to a user at a time.
        
        :param user: The user to whom the role will be added.
        :type user: User
        :param role: The role (Group) to be added to the user.
        :type role: Group
        :return: The user with the newly added role.
        :rtype: User    
    """
    if user.groups.exists():
        raise RoleAssignmentError()
    user.groups.add(role)
    logger.info(f"Roles [role: {role}] added for [user_id: {user.pk}]")
    return user