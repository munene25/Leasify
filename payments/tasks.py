from django.db import transaction
from common.emails import send_template_email
from common.tasks import email_task, critical_task
from billing.services import billing_period_complete
from payments.mpesa import STKResult
from payments.models import Payment
from payments import selectors as sl, services as sr
from payments.choices import PaymentStatus as PS


@email_task
def send_payment_notification(payment_id: int, additional_recepients: list[str] = []) -> list[str]:
    """Send payment receipt email to the user and additional recepients"""

    payment = Payment.objects.select_related("billing__tenancy__apartment", "billing__tenancy__user").get(pk=payment_id)
    user = payment.billing.tenancy.user

    # Fetch additional_recepients 
    recepients = [user.email, *additional_recepients]
    
    # Multiple recepients require email to be generic.
    send_template_email(
        subject="Payment has been received",
        context={"payment": payment},
        to=recepients,
        template_name="payments/payment_notification",
    )
    return recepients


@critical_task
@transaction.atomic
def payment_mpesa_process_async(stk_result: STKResult) -> dict[str, bool | str]:
    """This is an async processor for mpesa callbacks"""

    payment = sr.payment_mpesa_process(stk_result)

    if payment.status == PS.SUCCESS:
        billing = billing_period_complete(payment.billing)
        extra_recepients = sl.payment_get_extra_recepients()
        send_payment_notification.delay(payment.pk, extra_recepients)
        notification = True
    else:
        billing = payment.billing
        notification = False

    return {
        "payment": payment.status,
        "billing": billing.status,
        "tenancy": billing.tenancy.status,
        "notify": notification,
    }
