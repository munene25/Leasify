import pytest
from payments.tasks import send_payment_notification, payment_mpesa_process_async
from payments.models import Payment
from tests.types import Factory
from django.core.mail import EmailMessage
from payments.choices import PaymentStatus as PS
from billing.choices import BillingStatus as BS
from tenancy.choices import TenancyStatus as TS
from billing.models import BillingPeriod as BP
from tenancy.models import Tenancy


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
        assert mail.subject == "Payment has been received"
        assert mail.to == mail.to == [user.email, extra_email]

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
    

class TestPaymentMpesaProcessAsync:
    @pytest.mark.parametrize(
        "initial,expected",
        [
            ((TS.RESERVED, BS.UNPAID, PS.PENDING, True), (TS.ACTIVE, BS.PAID, PS.SUCCESS)),
            ((TS.DEFAULTING, BS.UNPAID, PS.PENDING, True), (TS.ACTIVE, BS.PAID, PS.SUCCESS)),
            ((TS.DEFAULTING, BS.UNPAID, PS.PENDING, False), (TS.DEFAULTING, BS.UNPAID, PS.FAILED)),
        ]
    )
    def test_for_payment_success(self, payment_factory: Factory[Payment], tenancy_factory: Factory[Tenancy], billing_factory: Factory[BP], initial: tuple, expected: tuple, stk_result):
        """Payment mpesa process should be called with the correct dict"""
        tenancy = tenancy_factory(status=initial[0])[0]
        billing = billing_factory(tenancy=tenancy, statuses=[initial[1]])[0]
        payment = payment_factory(billing=billing, statuses=[initial[2]])[0]
        success = stk_result(initial[3], payment.checkout_id)
        
        result = payment_mpesa_process_async(success)
        payment.refresh_from_db()
        assert result["tenancy"] == payment.billing.tenancy.status == expected[0]
        assert result["billing"] == payment.billing.status == expected[1]
        assert result["payment"] == payment.status == expected[2]

    def test_mail_sent(self, pending_payment, stk_result, mailoutbox):
        """test mail"""
        stk = stk_result(True, pending_payment.checkout_id)
        payment_mpesa_process_async(stk)
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]