from typing import TypedDict
from typing_extensions import Unpack
from structlog import getLogger
from users.models import User, Account
from django.db import transaction
from phonenumber_field.phonenumber import PhoneNumber

logger = getLogger("users.services,update")

class UserUpdateData(TypedDict, total=False):
    first_name: str
    last_name: str
    phone_number: PhoneNumber
    bio: str
    backup_email: str

@transaction.atomic
def user_change_password(*, user: User, new_password: str, current_password: str | None = None) -> User:
    """
    This service is used in both password recovery and password changes
    Therefore in password recovery flows, the current password is unknown
    Raw password is also required to check password validity

    :param user: User model instance
    :type user: User
    :param new_password: The password to be set if operation is successful
    :type new_password: str
    :param current_password: The current raw password of the user. Can be none in password recovery flows
    :type current_password: str

    :return: Modified User object
    :rtype: User 
    """
    if current_password:
        user.check_password(current_password)
    setattr(user, "_raw_password", new_password)
    user.set_password(new_password)
    user.full_clean()
    user.save()
    logger.info(f"user [user_id: {user.pk}] password changed")
    # TODO: Implement mail sending to notify user
    # TODO: Invalidate refresh token
    return user



@transaction.atomic
def user_update(user: User,  **kwargs: Unpack[UserUpdateData]) :
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
    
    account: Account = user.account # type: ignore
    
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

