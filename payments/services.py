import requests
from structlog import get_logger
from typing import TYPE_CHECKING
from django.db import transaction
from common.exceptions import MpesaAPIError
from payments.models import Payment
from payments import selectors as sl
from payments.choices import PaymentStatus as PS, PaymentMode as PM
from billing.choices import BillingStatus as BS
from billing.models import BillingPeriod as BP
from rest_framework.exceptions import ValidationError
from payments.mpesa import initiate_stk_push, query_payment_status, make_timestamp
from payments import tasks

logger = get_logger("payments")

if TYPE_CHECKING:
    from payments.mpesa import STKResult
    from users.models import User
    from billing.models import BillingPeriod as BP


@transaction.atomic
def payment_mpesa_initiate(*, billing: "BP", phone_number: str, idempotency_key: str) -> Payment:
    """
    Initialize a payment via M-Pesa STK push.

    Creates a new payment record and initiates an M-PESA STK push transaction to collect payment from the user.

    :param billing: The billing period being paid for (ForeignKey reference)
    :param phone_number: The mobile phone number of the payer for STK push notification
    :param idempotency_key: Unique key to prevent duplicate payments
    :returns: Payment object created or retrieved from cache

    """

    billing = BP.objects.select_for_update().get(pk=billing.pk)

    # Prevents CANCELLED OR PAID billings to be processed
    if billing.status != BS.UNPAID:
        raise ValidationError(f"Payment not allowed for {billing.status} billing")

    # Check for Idempotency
    if existing := billing.payments.filter(idempotency_key=idempotency_key).first():
        return existing

    # Check for Pending
    if pending := billing.payments.filter(status=PS.PENDING).first():
        return pending

    try:
        timestamp = make_timestamp()
        res = initiate_stk_push(
            phone_number=phone_number,
            amount=int(billing.total_due),
            account_ref=billing.name[:8],
            description="Rent Payment",
            timestamp=timestamp,
        )
    except (requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
        if e.response:
            status_code = e.response.status_code
            message = e.response.json()
        logger.error("stk_push_failed", status_code=status_code or None, response=message)
        raise MpesaAPIError() from e

    payment = Payment.objects.create(
        billing=billing,
        amount=billing.total_due,
        status=PS.PENDING,
        payment_mode=PM.MPESA,
        phone_number=phone_number,
        checkout_id=res["checkout_id"],
        idempotency_key=idempotency_key,
        timestamp=timestamp,
    )

    logger.info("payment_initiated", payment_id=payment.pk, billing_id=billing.pk, idemp_key=idempotency_key)
    return payment


def payment_alt_create(*, billing: "BP", mode: PM, recorded_by: "User", status: PS = PS.SUCCESS) -> Payment:
    """
    Create a manual payment via an alternate mode (CASH/BANK).

    :param billing: The billing period being paid for
    :param mode: The payment mode (CASH/BANK)
    :param recorded_by: The user who created this manual payment
    :param status: Initial status of the payment
    :returns: Payment object created with specified status

    """
    # Prevents CANCELLED OR PAID billings to be processed
    if billing.status != BS.UNPAID:
        raise ValidationError(f"Payment not allowed for {billing.status} billing")

    payment = Payment.objects.create(
        billing=billing,
        amount=billing.total_due,
        status=status,
        payment_mode=mode,
        recorded_by=recorded_by,
    )

    logger.info(
        "payment_alt_created",
        payment_id=payment.pk,
        billing_id=billing.pk,
        payment_mode=mode,
    )

    return payment


def payment_mpesa_process(stk_result: "STKResult") -> Payment:
    """
    Process M-Pesa callback and update payment status accordingly.
    Sends emails to the user and extra selected recepients

    :param stk_result: The payment response containing checkout details and transaction result
    :returns: Updated Payment object with new status

    """
    payment = sl.payment_get_checkout(stk_result["checkout_id"])

    payment.status = PS.SUCCESS if stk_result["success"] else PS.FAILED
    payment.receipt_no = stk_result["receipt_no"]

    payment.save(update_fields=["status", "receipt_no"])

    extra_recepients = sl.payment_get_extra_recepients()
    tasks.send_payment_notification.delay(payment.pk, extra_recepients)

    logger.info(
        "payment_processed",
        payment_id=payment.pk,
        checkout_id=payment.checkout_id,
        status=payment.status,
        description=stk_result["result_desc"],
    )
    return payment


def payment_mpesa_query(payment: Payment) -> Payment:
    """
    Query the status of an M-Pesa payment via the MPESA endpoint and update the payment.

    :param payment: The payment object to query
    :returns: Updated Payment object with new status

    """
    if not payment.checkout_id or not payment.timestamp:
        raise MpesaAPIError("Only M-PESA payments can be queried")

    if payment.status != PS.PENDING:
        return payment

    try:
        stk_result = query_payment_status(checkout_id=payment.checkout_id, timestamp=payment.timestamp)
    except (requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
        if e.response:
            status_code = e.response.status_code
            message = e.response.json()
        logger.error("payment_query_failed", status_code=status_code or None, response=message)
        raise MpesaAPIError() from e

    return payment_mpesa_process(stk_result)
