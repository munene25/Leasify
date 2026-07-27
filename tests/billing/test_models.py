import pytest
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from tests.types import Factory
from datetime import date, timedelta
from billing.models import BillingPeriod
from billing.choices import BillingStatus as BS
from tenancy.models import Tenancy
from users.models import User
from apartments.models import Apartment
from common.period import DateRange, today


class TestBillingPeriodModel:

    def test_is_current(self, billing_factory: Factory[BillingPeriod]):
        """Verify is_current reflects billing period status."""
        billings = billing_factory(statuses=[BS.PAID, BS.CANCELLED, BS.UNPAID], duration=1)
        assert billings[0].is_current == True
        assert billings[1].is_current == False
        assert billings[2].is_current == False

    def test_next_start_raises_for_cancelled(self, billing_factory: Factory[BillingPeriod]):
        """next_start should raise for cancelled billing periods."""
        cancelled = billing_factory(statuses=[BS.CANCELLED])[0]
        with pytest.raises(ValidationError):
            cancelled.next_start

    def test_next_start_returns_day_after_end(self, billing_factory: Factory[BillingPeriod]):
        """next_start should return the day after end_date."""
        paid = billing_factory(statuses=[BS.PAID])[0]
        assert paid.next_start == paid.end_date + timedelta(1)

    def test_duration_months(self, tenancy: Tenancy):
        """Verify duration_months is calculated correctly."""
        r = DateRange.for_month()
        next = r.next_month()

        one_month =  BillingPeriod.objects.create(
            tenancy=tenancy,
            start_date=r.start_date,
            end_date=r.end_date,
            status=BS.PAID,
            total_due=10_000
        )
        assert one_month.duration_months == 1

        two_months = BillingPeriod.objects.create(
            tenancy=tenancy,
            start_date=r.start_date,
            end_date=next.end_date,
            status=BS.PAID,
            total_due=10_000
        )
        assert two_months.duration_months == 2

    def test_str_and_name(self, billing_factory: Factory[BillingPeriod]):
        """Verify __str__ and name and contains month abbreviation."""
        unpaid = billing_factory(statuses=[BS.UNPAID], starting=date(2022, 1, 1))[0]
        assert str(unpaid) == "[JAN-2022][JAN-2022]"
        assert unpaid.name == "Jan 2022"

        paid = billing_factory(statuses=[BS.UNPAID], starting=date(2022, 1, 1), duration=2)[0]
        assert str(paid) == "[JAN-2022][FEB-2022]"
        assert paid.name == "Jan 2022 to Feb 2022" 

    def test_unique_constraint(self, billing_factory: Factory[BillingPeriod]):
        """Verify duplicate billing period raises IntegrityError."""
        billing = billing_factory(statuses=[BS.UNPAID])[0]
        with pytest.raises(IntegrityError):
            BillingPeriod.objects.create(
                tenancy=billing.tenancy,
                start_date=billing.start_date,
                end_date=billing.end_date,
                status=BS.UNPAID,
                total_due=10000,
            )