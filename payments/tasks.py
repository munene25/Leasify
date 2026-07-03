from payments.models import PaymentStatus, Payment
from payments import services as sr
from common.emails import send_template_email
from common.tasks import email_task, regular_task
from payments.mpesa import STKResult

@email_task
def send_payment_notification(payment_id: int, additional_recepients: list[str] = []) -> dict[str, list]:
    """Send payment receipt email to the user and additional recepients"""

    payment = Payment.objects.select_related("billing__tenancy__apartment", "billing__tenancy__user").get(pk=payment_id)
    user = payment.billing.tenancy.user

    context = {
        "received_from": user.full_name,
        "receipt_no": payment.receipt_no or "N/A",
        "payment": payment,
        "status": "SUCCESS" if payment.status == PaymentStatus.SUCCESS else "FAILED",
        "receipt_date": payment.created_at.strftime("%d %b %Y, %I:%M %p"),
    }
    # In order to send emails to both the payer and additional_recepients the email should be as generic as possible.
    recepients = [user.email, *additional_recepients]
    send_template_email(
        subject="Payment received",
        context=context,
        to=recepients, 
        template_name="payments/payment_notification",
    )
    return {"Payment notification sent": recepients}

@regular_task
def payment_mpesa_process_async(stk_result: STKResult):
    """This is an async processor for mpesa callbacks"""
    sr.payment_mpesa_process(stk_result)