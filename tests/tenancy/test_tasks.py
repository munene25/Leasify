import pytest
from datetime import timedelta
from tests.types import Factory
from billing.choices import BillingStatus as BS
from billing.models import BillingPeriod
from tenancy.models import Tenancy, DEFAULT_RESERVATION_DURATION
from tenancy.choices import TenancyStatus as TS, TerminationReason as TS
from tenancy.tasks import *
from freezegun import freeze_time
from django.utils import timezone
from common.period import today as _today
from django.core.mail import EmailMessage

# define a helper to quickly change status
def status_to(tenants: list[Tenancy], status: BS) -> None:
    BillingPeriod.objects.filter(tenancy_id__in=[t.pk for t in tenants]).update(status=status)


class TestTenancyActiveSetDefaulting:

    def test_active_set_defaulting_successful(self, tenancy_factory: Factory[Tenancy]):
        """
        Create 5 tenancies.
        Set status is active,
        Set billing period is PAID CANCELLED OR UNPAID(default)
        Only Paid should be spared from transition
        """

        tenants = tenancy_factory(5)
        paid_tenants = tenants[:2]
        unpaid_tenants = tenants[2:4]
        cancelled_tenants = tenants[4:]

        status_to(paid_tenants, BS.PAID)
        assert paid_tenants[0].billings.latest("start_date").status == BS.PAID
        status_to(cancelled_tenants, BS.CANCELED)
        assert cancelled_tenants[0].billings.latest("start_date").status == BS.CANCELED

        ids = set(active_set_defaulting())
        assert {t.pk for t in [*unpaid_tenants, *cancelled_tenants]} == ids

        # sample paid tenant status.
        paid_tenant = paid_tenants[0]
        paid_tenant.refresh_from_db()
        assert paid_tenant.status == TS.ACTIVE

        # sample cancelled tenant status.
        cancelled_tenant = cancelled_tenants[0]
        cancelled_tenant.refresh_from_db()
        assert cancelled_tenant.status == TS.DEFAULTING

        # sample unpaid tenant status.
        unpaid_tenant = unpaid_tenants[0]
        unpaid_tenant.refresh_from_db()
        assert unpaid_tenant.status == TS.DEFAULTING

    def test_in_case_of_no_billing_period(self, actual_tenant: Tenancy):
        """Should also work for tenancies that do not have a billing period"""

        actual_tenant.billings.latest("start_date").delete()
        actual_tenant.status = TS.ACTIVE
        actual_tenant.save(update_fields=["status"])

        assert len(active_set_defaulting()) == 1
        actual_tenant.refresh_from_db()
        assert actual_tenant.status == TS.DEFAULTING

    def test_active_to_defaulting_no_of_queries(self, tenancy_factory: Factory[Tenancy], django_assert_num_queries):
        """
        1. list pks.
        2. update tenancies
        """
        tenancy_factory(2)
        with django_assert_num_queries(2):
            active_set_defaulting()


class TestReservedSetTerminated:

    def test_reserved_set_terminated_successful(self, tenancy_factory: Factory[Tenancy]):
        """
        First create tenants in status of reserved today.
        Expiry will be set DEFAULT_EXPIRY_DURATION days ahead of today.
        All reserved tenancies beyound expiry should be set to TERMINATED.
        """
        now = timezone.now()

        one_day_later = now + timedelta(1)
        after_expiry = now + DEFAULT_RESERVATION_DURATION + timedelta(1)

        tenants = tenancy_factory(2, overrides={"status": TS.RESERVED})
        t = tenants[0]
        assert t.billings.filter(status=BS.UNPAID).count() == 1

        with freeze_time(now, tz_offset=0) as frozen:
            assert tenants[0].reservation_expiry == _today() + timedelta(days=2)

            # try and terminate on the day of.
            assert reserved_set_terminated() == []

            # try and terminate 1 day after
            frozen.move_to(one_day_later)
            assert reserved_set_terminated() == []

            frozen.move_to(after_expiry)
            assert len(reserved_set_terminated()) == len(tenants)

            # sample tenants and check status:
            
            t.refresh_from_db()
            assert t.status == TS.TERMINATED
            assert t.termination_date == _today()
            assert t.termination_reason == TR.EXPIRED

            # now check the status of their last billing
            assert t.billings.filter(status=BS.UNPAID).count() == 0
    
    def test_reserved_set_terminated_no_querries(self, actual_tenant: Tenancy, django_assert_num_queries):
        """
        1. open transaction
        2. get list.
        3. update tenancy.
        4. update billings.
        5. close transaction
        """
        past_expiry = timezone.now() + DEFAULT_RESERVATION_DURATION + timedelta(1)
        with freeze_time(past_expiry) as frozen:
            with django_assert_num_queries(5):
                reserved_set_terminated()

class TestDefaultingSetTerminated:

    def test_defaulting_set_terminated_successful(self, tenancy_factory: Factory[Tenancy]):
        """
        For defaulting tenants move them to terminated and provide reason.
        """
        defaulting = tenancy_factory(2, overrides={"status": TS.DEFAULTING})
        active = tenancy_factory(2, overrides={"status": TS.ACTIVE})

        assert {t.pk for t in defaulting} == set(defaulting_set_terminated())
        t = defaulting[0]
        t.refresh_from_db()
        assert t.status == TS.TERMINATED
        assert t.termination_reason ==  TR.NONPAYMENT
        assert t.billings.filter(status=BS.UNPAID).count() == 0

class TestNotifyReservedOnExpiry:
    def test_reserved_on_expiry_queries_correct_list(self, tenancy_factory: Factory[Tenancy], mailoutbox: list[EmailMessage]):
        """Those whose expiry is tomorrow should be included"""

        tenants = tenancy_factory(3, overrides={"status": TS.RESERVED})
        day_of_expiry = timezone.now() + DEFAULT_RESERVATION_DURATION - timedelta(1)

        with freeze_time(day_of_expiry):
            assert set(notify_reserved_on_expiry()) == {t.pk for t in tenants}

    def test_reserved_notify_expiry(self, actual_tenant: Tenancy, mailoutbox: list[EmailMessage]):
        """We need to check the mail message. Verify apartment_name, tenant_name, max_reservations, payment_url"""

        from tests.helpers import check_links_in_mail
        tommorrow = today() + timedelta(1)
        actual_tenant.reservation_expiry = tommorrow
        actual_tenant.save(update_fields=["reservation_expiry"])

        notify_reserved_on_expiry()
        assert len(mailoutbox) == 1
        
        mail = mailoutbox[0]
        check_links_in_mail(actual_tenant.user, mail, "payments/initiate")
        assert "reservation is about to expire" in mail.subject
        assert actual_tenant.apartment.apartment_name in mail.body
        assert actual_tenant.user.full_name in mail.body
        assert str(MAX_RESERVATIONS_PER_USER) in mail.body
