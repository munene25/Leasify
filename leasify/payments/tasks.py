from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError
from leasify.common.emails import send_template_email
from leasify.common.tasks import email_task, critical_task
from leasify.billing.services import billing_period_complete
from leasify.payments import selectors as sl
from leasify.payments.mpesa import STKResult
from leasify.payments.models import Payment
from leasify.payments import services as sr
from leasify.payments.choices import PaymentStatus as PS


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
def payment_mpesa_process_async(stk_result: STKResult) -> dict[str, str]:
    try:
        payment = sr.payment_mpesa_process(stk_result)
    except ValidationError as e:
        return {"task_status": "Skipped", "description": str(e.detail)}
    except NotFound as e:
        return {"task_status": "Failed", "description": str(e.detail)}

    if payment.status == PS.SUCCESS:
        billing_period_complete(payment.billing)
        extra_recipients = sl.payment_get_extra_recipients()
        transaction.on_commit(
            lambda: send_payment_notification.delay(payment.pk, extra_recipients)
        )

    return {
        "task_status": "Success",
        "description": f"Payment {payment.status}, Billing {payment.billing.status}, Tenancy {payment.billing.tenancy.status}",
    }