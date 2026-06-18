from payments.models import PaymentStatus, Payment
from config.emails import send_template_email


def send_payment_notification(payment_id: int, additional_recepients: list[str] = []):
    """Send payment receipt email to the user with PDF attachment."""

    payment = Payment.objects.select_related("billing__tenancy__apartment", "billing__tenancy__user").get(pk=payment_id)
    user = payment.billing.tenancy.user

    context = {
        "received_from": user.full_name,
        "receipt_no": payment.receipt_no or "N/A",
        "payment": payment,
        "status": "SUCCESS" if payment.status == PaymentStatus.SUCCESS else "FAILED",
        "receipt_date": payment.created_at.strftime("%d %b %Y, %I:%M %p"),
    }
    # ? Also send to the maager/caretaker etc
    # ? In order to do so the email should be as generic as possible.
    send_template_email(
        subject="Payment received",
        context=context,
        to=[user.email, *additional_recepients], 
        template_name="payments/payment_notification",
    )
