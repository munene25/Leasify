from typing import TYPE_CHECKING
from payments.models import Payment
from django.db import transaction
from rest_framework.exceptions import ValidationError
from payments.choices import PaymentStatus, PaymentInitiator
from structlog import get_logger
from uuid import uuid4

logger = get_logger("payments.services")

if TYPE_CHECKING:
    from payments.mpesa import CallbackResponse
    from billing.models import BillingPeriod


@transaction.atomic
def payment_initiate(
    billing: "BillingPeriod",
    phone_number: str,
    initiator: PaymentInitiator,
    stk_push: bool = False,
) -> Payment:
    """
    Initialize a payment. Depending on status can be updated later on callback

    :param billing:
    :param transaction_type:
    :param status:
    :param phone_number: phone number to
    :param initiator: The short code for who is initiating the request. determined upstream

    """
    # ? if initiator is tenant dont allow status confirmed?
    
    if stk_push:
        from payments.mpesa.stk_push import intiate_stk_push

        r = intiate_stk_push(
            phone_number=phone_number,
            amount=int(billing.total_due),
            account_ref=str(billing),
            description="Rent Payment",
        )
        checkout_id = r.checkout_id
    else:
        checkout_id = str(uuid4())

    payment = Payment(
        billing=billing,
        phone_number=phone_number,
        amount=billing.total_due,
        status=PaymentStatus.PENDING,
        checkout_id=checkout_id,
        initiator=initiator,
        payee=billing.tenancy.user.full_name
    )

    payment.full_clean()
    payment.save()

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
def payment_confirm(r: "CallbackResponse") -> Payment:
    """
    Parse callback response and return an upadted payment.
    Update the payment status and receipt no if it's successfull
    """

    checkout_id = r.checkout_id

    payment = Payment.objects.select_for_update().get(checkout_id=checkout_id)

    if payment.status in [PaymentStatus.FAILED, PaymentStatus.SUCCESS]:
        raise ValidationError("Operation not allowed, payment already closed")

    payment.status =  PaymentStatus.SUCCESS if r.success else PaymentStatus.FAILED

    if r.success:
        payment.receipt_no = r.receipt_no
    
    # Generate receipt?

    payment.full_clean()
    payment.save()
    logger.info("payment_confirmed", checkout_id=payment.checkout_id, status=payment.status)
    return payment
