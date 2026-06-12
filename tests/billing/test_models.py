import pytest
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from django.db import models
from datetime import date, timedelta
from billing.models import BillingPeriod
from billing.choices import BillingStatus as BS
from tenancy.models import Tenancy
from users.models import User
from apartments.models import Apartment
from common.period import DateRange, today


def test_billing_period_model(today: date):
    r = DateRange.for_month()
    prev = r.previous_month()
    a = Apartment.objects.create(
        block="NEW",
        unit_number=1,
        rent=10000,
    )
    u = User.objects.create(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password="test"
    )
    t = Tenancy.objects.create(
        user=u,
        apartment=a,
        date_joined=today,
    )
    paid = BillingPeriod.objects.create(
        tenancy=t,
        start_date=prev.start_date,
        end_date=prev.end_date,
        status=BS.PAID,
        total_due=10000,
    )
    canceled = BillingPeriod.objects.create(
        tenancy=t,
        start_date=r.start_date,
        end_date=r.end_date,
        status=BS.CANCELED,
        total_due=10000,
    )
    unpaid = BillingPeriod.objects.create(
        tenancy=t,
        start_date=r.start_date,
        end_date=r.next_month().end_date,
        status=BS.UNPAID,
        total_due=10000,
    )
    # test properties
    assert not paid.is_current
    assert canceled.is_current
    assert unpaid.is_current

    # test next_start
    with pytest.raises(ValidationError):
        canceled.next_start

    assert paid.next_start == paid.end_date + timedelta(1)
    
    # test duration_months
    assert canceled.duration_months == 1
    assert unpaid.duration_months == 2

    # test __str__ and name
    assert str(unpaid) == unpaid.name
    assert today.strftime("%b").upper() in unpaid.name

    # Check constraints:
    with pytest.raises(IntegrityError):
        BillingPeriod.objects.create(
            tenancy=t,
            start_date=r.start_date,
            end_date=r.next_month().end_date,
            status=BS.UNPAID,
            total_due=10000,
        )

    