import requests
from structlog import get_logger
from typing import TYPE_CHECKING
from payments.models import Payment
from payments.choices import PaymentStatus, PaymentMode
from payments.mpesa.stk_push import initiate_stk_push  # Use original function name from stk_push.py (typo preserved)
from common.exceptions import PaymentError
from payments.selectors import payment_get_checkout

logger = get_logger("payments")

if TYPE_CHECKING:
    from payments.mpesa import CallbackResponse
    from users.models import User
    from billing.models import BillingPeriod as BP


def payment_mpesa_initiate(*, billing: "BP", phone_number: str) -> Payment:
    """
    Initialize a payment via M-Pesa STK push. Depending on status can be updated later on callback.

    :param billing: The billing period being paid for
    :param phone_number: Phone number that initiated the transaction
    :returns: Payment object created with PENDING status

    """

    try:
        res = initiate_stk_push(
            phone_number=phone_number,
            amount=int(billing.total_due),
            account_ref=billing.name[:8],  # example: JAN-2024
            description="Rent Payment",
        )
    except (requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
        logger.error(
            "stk_push_failed",
            status_code=getattr(e.response, "status_code", None),
            response=(e.response.json()),  # type: ignore
        )
        raise PaymentError()

    payment = Payment.objects.create(
        billing=billing,
        amount=billing.total_due,
        status=PaymentStatus.PENDING,
        payment_mode=PaymentMode.MPESA,
        phone_number=phone_number,
        checkout_id=res.checkout_id,
    )

    logger.info(
        "payment_initiated",
        tenancy_id=billing.tenancy_id,
        billing_id=billing.pk,
        billing=billing.name,
        amount=billing.total_due,
        phone=payment.phone_number,
    )
    return payment


def payment_alt_create(*, billing: "BP", mode: PaymentMode, recorded_by: "User", status: PaymentStatus = PaymentStatus.SUCCESS):
    """
    Create a manual payment via an alternate mode (CASH/BANK).

    :param billing: The billing period being paid for
    :param mode: The payment mode (CASH/BANK)
    :param recorded_by: The user who created this manual payment
    :param status: Initial status of the payment
    :returns: Payment object created with specified status

    """

    payment = Payment.objects.create(
        billing=billing,
        amount=billing.total_due,
        status=status,
        payment_mode=mode,
        recorded_by=recorded_by,
    )

    logger.info(
        "payment_alt_created",
        payment_pk=payment.pk,
        billing=billing.name,
        amount=billing.total_due,
        payment_mode=mode,
    )

    return payment


def payment_mpesa_process(cb: "CallbackResponse") -> Payment:
    """
    Process M-Pesa callback and update payment status accordingly.

    :param cb: The callback response containing checkout details and transaction result
    :returns: Updated Payment object with new status

    """
    payment = payment_get_checkout(cb.checkout_id)
    if cb.success:
        payment.status = PaymentStatus.SUCCESS
        payment.receipt_no = cb.receipt_no
    else:
        payment.status = PaymentStatus.FAILED

    payment.save()
    # ? Send email notification
    logger.info("payment_processed", checkout_id=payment.checkout_id, status=payment.status, description=cb.result_desc)
    return payment
