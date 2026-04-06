from typing import TypedDict
from typing_extensions import Unpack
from structlog import getLogger
from users.models import User
from django.db import transaction
from rest_framework.exceptions import ValidationError
from phonenumber_field.phonenumber import PhoneNumber
from users.tasks import notify_password_change

logger = getLogger("users.services,update")

class UserUpdateData(TypedDict, total=False):
    """Represents the payload expected for the user_update function"""
    first_name: str
    last_name: str
    phone_number: PhoneNumber
    bio: str
    backup_email: str



@transaction.atomic
def user_update(user: User,  **kwargs: Unpack[UserUpdateData]):
    """
    User and Account model updates under a singular interface.
    
    :param user: User to be used as the related field
    :type user: User
    :param kwargs:
        first_name: str, 
        last_name: str, 
        phone_number: PhoneNumber, 
        bio: str, 
        backup_email: str
    :type kwargs: dict

    :return: Modified User object
    :rtype: User
    """      
    USER_FIELDS = {"first_name", "last_name"}
    ACCOUNT_FIELDS = {"phone_number", "bio", "backup_email"}

    user_updates = []
    account_updates = []
    
    account = user.account 
    
    # Normalize email
    backup_email = kwargs.get("backup_email", None)
    if backup_email:
        kwargs["backup_email"] = User.objects.normalize_email(backup_email)

    for field, value in kwargs.items():

        if field in USER_FIELDS and getattr(user, field, value) != value:
            setattr(user, field, value)
            user_updates.append(field)
        
        elif field in ACCOUNT_FIELDS and getattr(account, field, value) != value:
            setattr(account, field, value)
            account_updates.append(field)
    
    if user_updates:
        user.full_clean()
        user.save(update_fields=user_updates)
        logger.info(f"user [user_id: {user.pk}] data modified. fields: {user_updates}")
    
    if account_updates:
        account.full_clean()
        account.save(update_fields=account_updates)
        logger.info(f"account [account_id: {account.pk}] modified. fields: {account_updates}")

    return user


@transaction.atomic
def user_change_password(*, user: User, new_password: str, password: str | None = None, is_ressetting: bool =False) -> User:
    """
    This service is used in both password recovery and password changes
    Therefore in password recovery flows, the current password is unknown
    Raw password is also required to check password validity


    :param user: User model instance
    :type user: User
    :param new_password: The password to be set if operation is successful
    :type new_password: str
    :param password: The current raw password of the user. Can be none in password recovery flows
    :type password: str | None

    :return: Modified User object
    :rtype: User 
    """
    # ! Password changes automatically invalidate issued cookies
    # ! CRITICAL BUG Found
    # Calling check_password does not raise an error
    # To mitigate this an explicit flag guarantees the password is checked.
    # Also necessary to call **validate_password** not 'check_password'

    if not is_ressetting:
        if not password:
            raise ValidationError({"password": "Please provide a password"})
        else:
            user.validate_password(password)

    user.set_password(new_password)
    user.full_clean()
    user.save(update_fields=["password"])
    logger.info(f"user [user_id: {user.pk}] password changed")
    transaction.on_commit(lambda: notify_password_change.delay(user.pk))
    return user




