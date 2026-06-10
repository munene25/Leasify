from datetime import date

import pytest
from tenancy.models import Tenancy
from tenancy.services import tenancy_create
from tenancy.choices import *
from billing.models import BillingPeriod
from billing.choices import *
from common.period import DateRange
from django.db import IntegrityError

from tests.types import Factory
from users.models import User


def test_tenancy_model_properties(user, apartment, today):
    r = DateRange.for_month()
    t = Tenancy.objects.create(
        user=user,
        apartment=apartment,
        date_joined=today,
        status=TenancyStatus.ACTIVE,
    )

    b_unpaid = BillingPeriod.objects.create(
        tenancy=t,
        start_date=r.start_date,
        end_date=r.end_date,
        status=BillingStatus.UNPAID,
        total_due=20000,
    )

    assert t.is_continuing is True
    assert t.has_pending_bills is True
    assert t.last_paid_billing is None
    assert t.paid_up_to is None

    b_unpaid.status = BillingStatus.CANCELED
    b_unpaid.save()

    assert t.has_pending_bills is False
    assert t.last_paid_billing is None
    assert t.paid_up_to is None

    b_paid = BillingPeriod.objects.create(
        tenancy=t,
        start_date=r.start_date,
        end_date=r.end_date,
        status=BillingStatus.PAID,
        total_due=20000,
    )

    # force DB re-evaluation, not cache hacking
    t.refresh_from_db()

    assert t.last_paid_billing == b_paid
    assert t.paid_up_to == b_paid.end_date

def test_user_unique_active_pending_constraint(user, apartment, today):
    Tenancy.objects.create(
        user=user,
        apartment=apartment,
        status=TenancyStatus.ACTIVE,
        date_joined=today,
    )
    with pytest.raises(IntegrityError):
        Tenancy.objects.create(
        user=user,
        apartment=apartment,
        status=TenancyStatus.RESERVED,
        date_joined=today,
    )

def test_apartment_unique_active_pending_constraint(user, apartment, user_factory: Factory[User]):
    Tenancy.objects.create(
        user=user,
        apartment=apartment,
        status=TenancyStatus.ACTIVE,
        date_joined=date.today(),
    )
    other_user = user_factory()[0]
    with pytest.raises(IntegrityError):
        Tenancy.objects.create(
            user=other_user,
            apartment=apartment,
            status=TenancyStatus.RESERVED,
            date_joined=date.today(),
        )