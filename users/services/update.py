from structlog import getLogger
from users.models import User, Account
from django.db import transaction


logger = getLogger("users.services,update")


@transaction.atomic
def user_change_password(*, user: User, new_password: str, current_password: str | None = None) -> User:
    """
    This service is used in both password recovery and password changes
    Therefore in password recovery flows, the current password is unknown
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
def user_update(user: User,  **kwargs):
    """
    Brings user and account models updates under a singular interface
    """      
    USER_FIELDS = {"first_name", "last_name"}
    ACCOUNT_FIELDS = {"phone_number", "bio", "backup_email"}

    user_updates = []
    account_updates = []
    
    account: Account = user.account # type: ignore
    
    for field, value in kwargs.items():

        if field in USER_FIELDS and getattr(user, field, value) != value:
            setattr(user, field, value)
            user_updates.append(field)
        
        elif field in ACCOUNT_FIELDS and getattr(account, field, value) != value:
            setattr(account, field, value)
            account_updates.append(field)

    # Short circuit
    if not (account_updates or user_updates):
        return user
    
    if user_updates:
        user.full_clean()
        user.save(update_fields=user_updates)
        logger.info(f"user [user_id: {user.pk}] data modified. fields: {user_updates}")
    
    if account_updates:
        account.full_clean()
        account.save(update_fields=account_updates)
        logger.info(f"account [account_id: {account.pk}] modified. fields: {account_updates}")

    return user

