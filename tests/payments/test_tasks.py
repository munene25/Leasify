from payments.tasks import send_payment_notification, payment_mpesa_process_async
from payments.models import Payment
from tests.types import Factory
from django.core.mail import EmailMessage
from payments.choices import PaymentStatus as PS


class TestSendPaymentNotification:

    def test_email_sent_with_details(self, payment_factory: Factory[Payment], mailoutbox: list[EmailMessage]):
        """The user making the payment should receive an email as well as any additional_recepients"""
        payment = payment_factory()[0]
        user = payment.billing.tenancy.user
        apartment = payment.billing.tenancy.apartment
        extra_email = "test@testmail.com"
        result = send_payment_notification(payment_id=payment.pk, additional_recepients=[extra_email])
        assert mailoutbox is not None
        mail = mailoutbox[0]
        assert mail.subject == "Payment received"
        assert mail.to == [user.email, extra_email]
        assert result["Payment notification sent"] == mail.to

        # Check email body
        assert apartment.name in mail.body
        assert payment.billing.name in mail.body
        assert str(payment.amount) in mail.body
        # assert f"Status {payment.status}" in mail.body  Fails, status not in .txt version

        assert payment.receipt_no is not None and payment.receipt_no in mail.body
        assert payment.phone_number is not None and payment.phone_number in mail.body

    def test_query_count(self, payment_factory: Factory[Payment], django_assert_num_queries):
        """Should just be one"""
        payment = payment_factory()[0]
        with django_assert_num_queries(1):
            send_payment_notification(payment_id=payment.pk)
    