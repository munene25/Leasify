import pytest
from typing import TYPE_CHECKING
from datetime import date, timedelta
from rest_framework.exceptions import ValidationError
from tenancy.models import Tenancy
from common.period import DateRange
from billing.models import BillingPeriod as BP
from payments.choices import PaymentStatus as PS
from payments.models import Payment
from tenancy.choices import TenancyStatus as TS
from billing.choices import BillingStatus as BS
from billing.services import billing_period_cancel, billing_period_complete, billing_period_create
from tests.types import Factory



class TestBillingPeriodCreate:
    def test_billing_period_create(self, tenancy_factory: Factory[Tenancy]):
        """
        This should create a new billing period for the given tenant and date range.
        """
        tenancy = tenancy_factory()[0]
        billing= billing_period_create(tenancy=tenancy,date_r=DateRange.compute_lease_window(date(2022, 1, 1), 2))
        assert BP.objects.count() == 1
        assert BP.objects.first() == billing
        assert billing.tenancy == tenancy

        # assert total due is duration months * apartment.rent

        rent = int(tenancy.apartment.rent)
        assert int(billing.total_due) == rent*2

        assert billing.start_date == date(2022, 1, 1)
        assert billing.end_date == date(2022, 2, 28)
        assert billing.status == BS.UNPAID

    def test_billing_periods_exceeding_max_allowed_raises(self, tenancy_factory: Factory[Tenancy]):
        """Should raise when the billing exceeds MAX_BILLING_PERIOD"""
        with pytest.raises(ValidationError):
            date_range = DateRange.compute_lease_window(date(2021, 1, 1), 5)
            billing_period_create(tenancy=tenancy_factory()[0], date_r=date_range)


class TestBillingPeriodCancel:
    def test_cancel_billing_periods_successful(self, billing_factory: Factory[BP]):
        """Should cancel the billing period"""
        billing = billing_factory(statuses=[BS.UNPAID])[0]
        assert BP.objects.count() == 1

        _billing = billing_period_cancel(billing)
        billing.refresh_from_db()
        assert billing == _billing
        
        assert billing.status == BS.CANCELED

    def test_cancelation_fails_for_non_unpaid_billings(self, billing_factory: Factory[BP]):
        """Should raise when the billing is not unpaid"""
        billing = billing_factory(statuses=[BS.PAID, BS.CANCELED])

        with pytest.raises(ValidationError):
            billing_period_cancel(billing[0])
        with pytest.raises(ValidationError):
            billing_period_cancel(billing[1])

class TestBillingPeriodComplete:
    def test_completion_sets_status_paid(self, billing_factory: Factory[BP], payment_factory: Factory[Payment]):
        """Should complete the billing period"""
        billing = billing_factory(statuses=[BS.UNPAID])[0]
        payment_factory(billing=billing)
        _billing = billing_period_complete(billing)
        billing.refresh_from_db()  # type: ignore
        assert billing == _billing
        
        assert billing.status == BS.PAID
    
    def test_sets_tenancy_active_if_billing_is_current(self, tenancy_factory: Factory[Tenancy], billing_factory: Factory[BP], payment_factory: Factory[Payment], today: date):
        """Should also set the tenancy active if it is current"""
        # setup tenancy and a paid billing period with a successful payment
        tenancy = tenancy_factory(statuses=[TS.RESERVED])[0]
        billing = billing_factory(tenancy=tenancy, statuses=[BS.UNPAID], starting=today)[0]
        # defaults success
        payment_factory(billing=billing)

        billing_period_complete(billing)
        tenancy.refresh_from_db()
        assert tenancy.status == TS.ACTIVE
        