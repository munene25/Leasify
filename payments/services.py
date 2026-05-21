from typing import Any, TYPE_CHECKING
from payments.models import Payment
from django.db import transaction
from rest_framework.exceptions import ValidationError
from payments.choices import TransactionType, PaymentStatus, PaymentInitiator 

from structlog import get_logger

logger = get_logger("payments.services")

if TYPE_CHECKING:
    from billing.models import BillingPeriod



@transaction.atomic
def payment_initiate(billing: "BillingPeriod", transaction_type: TransactionType, status: PaymentStatus, phone_number: str, initiator: PaymentInitiator, stk_push: bool) -> Payment:
    """
    Initialize a payment. Depending on status can be updated later on callback
    
    :param billing:
    :param transaction_type:
    :param status:
    :param phone_number: phone number to 
    :param initiator: The short code for who is initiating the request. determined upstream

    """
    
    if status == PaymentStatus.FAILED:
        raise ValidationError("Operation not allowed")
    
    #? if initiator is tenant dont allow status confirmed?

    payment = Payment(
        billing=billing,
        transaction_type=transaction_type,
        phone_number=phone_number,
        amount=billing.total_due,
        status=status,
        initiator=initiator,
    )
    payment.full_clean()
    payment.save()

    logger.info(
        "payment_initiated",
        tenancy_id=billing.tenancy_id,
        billing_period=str(billing),
        payment_amount=billing.total_due,
        status=status,
        phone_number=phone_number,
        payment_ref=payment.ref_no
    )
    if not stk_push:
        return payment
    
    if transaction_type == TransactionType.DEBIT and initiator == PaymentInitiator.TENANT:
        # initialize stk...
        raise NotImplemented("This is where the stk push request is initialized")
    
    raise ValidationError("You cannot perform an stk push for such a transaction")


@transaction.atomic
def payment_confirm(payment: Payment, payload: dict[str, Any]) -> Payment:
    """
    Assuming with a callback, this is where the validation happens and transaction status is changed

    :param payment: The payment instance to modify.
    :param payload: The payload in which to validate the status.
    """
    # validate payload:
    locked = Payment.objects.select_for_update().get(pk=payment.pk)
    if locked.status == PaymentStatus.CONFIRMED:
        raise ValidationError("Operation not allowed")
    
    # mock validation
    confirmation = payload.get("confirmed", None)
    

    new_status  = PaymentStatus.CONFIRMED if confirmation else PaymentStatus.FAILED

    if new_status == PaymentStatus.FAILED:
        # ?Could add a means of adding metadata on why
        pass

    locked.status = new_status

    locked.full_clean()
    locked.save()
    logger.info(
        "payment_confirmed",
        payment_ref=payment.ref_no
    )
    return locked
        
