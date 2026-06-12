from uuid import uuid4
from structlog import get_logger
from typing import TYPE_CHECKING
from django.db import transaction
from rest_framework.exceptions import ValidationError
from payments.models import Payment
from payments.mpesa.stk_push import intiate_stk_push
from payments.choices import PaymentStatus as PS, PaymentInitiator as PI

logger = get_logger("payments.services")

if TYPE_CHECKING:
    from payments.mpesa import CallbackResponse
    from billing.models import BillingPeriod as BP


@transaction.atomic
def payment_initiate(
    *, 
    billing: "BP", 
    initiator: PI, 
    stk_push: bool,
    phone_number:str, 
    paid_by: str,
    status: PS = PS.PENDING
) -> Payment:
    """
    Initialize a payment. Depending on status can be updated later on callback

    :param billing:
    :param transaction_type:
    :param status:
    :param phone_number: phone number that initiated the transaction
    :param initiator: The short code for who is initiating the request. determined upstream

    """
    
    if stk_push:
        r = intiate_stk_push(
            phone_number=phone_number,
            amount=int(billing.total_due),
            account_ref=billing.name[:8],
            description="Rent Payment",
        )
        checkout_id = r.checkout_id
    else:
        checkout_id = str(uuid4())

    payment = Payment.objects.create(
        billing=billing,
        phone_number=phone_number,
        amount=billing.total_due,
        status=status,
        checkout_id=checkout_id,
        initiator=initiator,
        paid_by=paid_by,
    )

    logger.info(
        "payment_initiated",
        tenancy_id=billing.tenancy_id,
        billing_period=billing.name,
        amount=billing.total_due,
        phone_number=payment.phone_number,
        payment_ref=payment.ref_no,
    )
    return payment


@transaction.atomic
def payment_confirm(cb: "CallbackResponse") -> Payment:
    """
    Parse callback response and return an upadted payment.
    Update the payment status and receipt no if it's successfull
    """

    checkout_id = cb.checkout_id
    payment = Payment.objects.select_for_update().get(checkout_id=checkout_id)

    if payment.status in [PS.FAILED, PS.SUCCESS]:
        raise ValidationError("Operation not allowed, payment already closed")

    payment.status =  PS.SUCCESS if cb.success else PS.FAILED

    if cb.success:
        payment.receipt_no = cb.receipt_no
    
    # ? Generate receipt?
    payment.save()
    logger.info("payment_confirmed", checkout_id=payment.checkout_id, status=payment.status)
    return payment
