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
from payments.mpesa import initiate_stk_push, query_payment_status, make_timestamp, parse_error
from payments import tasks

logger = get_logger("payments")

if TYPE_CHECKING:
    from payments.mpesa import STKResult
    from users.models import User
    from billing.models import BillingPeriod as BP


@transaction.atomic
def payment_mpesa_initiate(*, billing: "BP", phone_number: str, idempotency_key: str | None) -> Payment:
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
    if idempotency_key and (existing := billing.payments.filter(idempotency_key=idempotency_key).first()):
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
    except (requests.exceptions.RequestException) as e:
        status_code, message = parse_error(e)
        logger.error("stk_push_failed", status_code=status_code, response=message)
        raise MpesaAPIError() from e

    payment = Payment.objects.create(
        billing=billing,
        amount=billing.total_due,
        status=PS.PENDING,
        mode=PM.MPESA,
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

    :param billing: The billing period being paid for. Must have status UNPAID or CANCELLED.
    :param mode: The payment mode, either CASH or BANK.
    :param recorded_by: The user who created this manual payment record. Required for tracking accountability.
    :param status: Initial status of the payment, default is SUCCESS. Can be PENDING, SUCCESS, or FAILED.
    :returns: Payment object created with the specified billing and mode
    :raises ValidationError: If the billing status is not UNPAID or CANCELLED

    """
    # Prevents CANCELLED OR PAID billings to be processed
    if billing.status != BS.UNPAID:
        raise ValidationError(f"Payment not allowed for {billing.status} billing")

    payment = Payment.objects.create(
        billing=billing,
        amount=billing.total_due,
        status=status,
        mode=mode,
        recorded_by=recorded_by,
    )

    logger.info(
        "payment_alt_created",
        payment_id=payment.pk,
        billing_id=billing.pk,
        mode=mode,
    )

    return payment


def payment_mpesa_process(stk_result: "STKResult") -> Payment:
    """
    Process M-Pesa callback and update payment status accordingly.

    :param stk_result: The M-Pesa response containing checkout_id, success status, receipt_no, and result_desc
    :returns: Updated Payment object with new status (SUCCESS or FAILED)
    
    """
    payment = sl.payment_get_checkout(stk_result["checkout_id"])

    payment.status = PS.SUCCESS if stk_result["success"] else PS.FAILED
    payment.receipt_no = stk_result["receipt_no"]

    payment.save(update_fields=["status", "receipt_no"])

    logger.info(
        "payment_processed",
        payment_id=payment.pk,
        status=payment.status,
        description=stk_result["result_desc"],
    )
    return payment


def payment_mpesa_query(payment: Payment) -> STKResult:
    """
    Query the status of an M-Pesa payment via the MPESA endpoint.

    :param payment: The Payment object with a valid checkout_id and timestamp set for MPESA payments
    :returns: STKResult containing the payment status, receipt_no, and result_desc from M-Pesa
    :raises ValidationError: If the payment is not an M-PESA payment or has already completed (non-PENDING status)

    """
    if not payment.checkout_id or not payment.timestamp:
        raise ValidationError("Only M-PESA payments can be queried")

    if payment.status != PS.PENDING:
        raise ValidationError(f"'{payment.status.capitalize()}' payment cannot be queried")
    
    try:
        stk_result = query_payment_status(checkout_id=payment.checkout_id, timestamp=payment.timestamp)
    except (requests.exceptions.RequestException) as e:
        status_code, message = parse_error(e)
        logger.error("payment_query_failed", status_code=status_code, response=message)
        raise MpesaAPIError() from e

    logger.info(
        "payment_queried",
        payment_id=payment.pk,
        description=stk_result["result_desc"],
    )
    return stk_result

