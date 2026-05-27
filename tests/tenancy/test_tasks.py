import pytest
from datetime import timedelta
from tenancy.choices import *
from tests.types import Factory
from billing.choices import BillingStatus
from billing.models import BillingPeriod
from django.db.models import Q
from tenancy.models import Tenancy
from tenancy.tasks import tenancy_active_set_defaulting, tenancy_set_terminated_from
from freezegun import freeze_time
from django.utils import timezone
from common.period import today as _today
from tenancy.selectors import tenancy_in


# define a helper to quickly change status
def status_to(tenants: list[Tenancy], status: BillingStatus) -> None:
    BillingPeriod.objects.filter(tenancy_id__in=[t.pk for t in tenants]).update(status=status)


reserved_to_terminated = lambda: tenancy_set_terminated_from(
    initial=TenancyStatus.RESERVED,
    reason=TerminationReason.EXPIRED,
    filters=Q(reservation_expiry__lt=_today()),
)


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

        status_to(paid_tenants, BillingStatus.PAID)
        assert paid_tenants[0].billings.latest("start_date").status == BillingStatus.PAID
        status_to(cancelled_tenants, BillingStatus.CANCELED)
        assert cancelled_tenants[0].billings.latest("start_date").status == BillingStatus.CANCELED

        ids = set(tenancy_active_set_defaulting())
        assert {t.pk for t in [*unpaid_tenants, *cancelled_tenants]} == ids

        # sample paid tenant status.
        paid_tenant = paid_tenants[0]
        paid_tenant.refresh_from_db()
        assert paid_tenant.status == TenancyStatus.ACTIVE

        # sample cancelled tenant status.
        cancelled_tenant = cancelled_tenants[0]
        cancelled_tenant.refresh_from_db()
        assert cancelled_tenant.status == TenancyStatus.DEFAULTING

        # sample unpaid tenant status.
        unpaid_tenant = unpaid_tenants[0]
        unpaid_tenant.refresh_from_db()
        assert unpaid_tenant.status == TenancyStatus.DEFAULTING

    def test_in_case_of_no_billing_period(self, actual_tenant: Tenancy):
        """Should also work for tenancies that do not have a billing period"""

        actual_tenant.billings.latest("start_date").delete()
        actual_tenant.status = TenancyStatus.ACTIVE
        actual_tenant.save(update_fields=["status"])

        defaulting = tenancy_active_set_defaulting()
        assert len(defaulting) == 1
        actual_tenant.refresh_from_db()
        assert actual_tenant.status == TenancyStatus.DEFAULTING

    def test_active_to_defaulting_no_of_queries(self, tenancy_factory: Factory[Tenancy], django_assert_num_queries):
        """
        1. list pks.
        2. update tenancies
        """
        tenancy_factory(2)
        with django_assert_num_queries(2):
            tenancy_active_set_defaulting()


class TestTenancySetTerminatedFrom:

    def test_setting_reserved_to_terminated_successful(self, tenancy_factory: Factory[Tenancy]):
        """
        First create tenants in status of reserved.
        Freezegun fast forward DEFUALT_RESERVATION_EXPIRY days forward
        All reserved teancies should be set to Terminated.
        """
        now = timezone.now()

        one_day_later = now + timedelta(1)
        three_days_later = now + timedelta(3)

        tenants = tenancy_factory(2, overrides={"status": TenancyStatus.RESERVED})
        t = tenants[0]
        assert t.billings.filter(status=BillingStatus.UNPAID).count() == 1

        with freeze_time(now, tz_offset=0) as frozen:
            assert tenants[0].reservation_expiry == _today() + timedelta(days=2)

            # try and terminate on the day of.
            assert len(reserved_to_terminated()) == 0

            # try and terminate 1 day after
            frozen.move_to(one_day_later)
            assert len(reserved_to_terminated()) == 0

            frozen.move_to(three_days_later)
            assert len(reserved_to_terminated()) == len(tenants)

            # sample tenants and check status:
            
            t.refresh_from_db()
            assert t.status == TenancyStatus.TERMINATED
            assert t.termination_date == _today()
            assert t.termination_reason == TerminationReason.EXPIRED

            # now check the status of their last billing
            assert t.billings.filter(status=BillingStatus.UNPAID).count() == 0

    def test_tenancy_in_yields_correct_results(self, monkeypatch: pytest.MonkeyPatch, tenancy_factory: Factory[Tenancy]):
        now = timezone.now()
        one_day_later = now + timedelta(1)
        three_days_later = now + timedelta(3)

        tenants = tenancy_factory(5, overrides={"status": TenancyStatus.RESERVED})
        
        with freeze_time(three_days_later, tz_offset=0) as frozen:
            t = reserved_to_terminated()
            assert len(t) == 5