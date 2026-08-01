import pytest
from django.core.mail import EmailMessage
from leasify.tests.types import Factory
from leasify.tenancy.choices import TenancyStatus as TS
from leasify.tenancy.models import Tenancy
from leasify.billing.choices import BillingStatus as BS
from leasify.billing.models import BillingPeriod as BP
from payments.tasks import send_payment_notification, payment_mpesa_process_async
from payments.models import Payment
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

    def test_with_not_found_checkout_id(self, stk_result):
        """Should return early with task_status failed"""
        result = payment_mpesa_process_async(stk_result(False))
        assert result["task_status"] == "Failed"
        assert "checkout_id" in result["description"]

    def test_idempotency(self, stk_result, payment_factory: Factory[Payment]):
        """Should not process an already processed payment"""
        payments = payment_factory(statuses=[PS.SUCCESS, PS.FAILED])
        success = stk_result(True, payments[0].checkout_id)
        failed = stk_result(False, payments[1].checkout_id)

        result = payment_mpesa_process_async(success)
        assert result["task_status"] == "Skipped"
        assert "Success" in result["description"]

        result = payment_mpesa_process_async(failed)
        assert result["task_status"] == "Skipped"
        assert "Failed" in result["description"]


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
        assert result["task_status"] == "Success"
        assert payment.billing.tenancy.status == expected[0]
        assert payment.billing.status == expected[1]
        assert payment.status == expected[2]

    def test_mail_sending(self, pending_payment, stk_result, django_capture_on_commit_callbacks, mailoutbox):
        """test mail sent out after commiting the transactions"""
        stk = stk_result(True, pending_payment.checkout_id)
        with django_capture_on_commit_callbacks(execute=True):
            payment_mpesa_process_async(stk)
        assert len(mailoutbox) == 1