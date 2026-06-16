import pytest
from typing import TYPE_CHECKING
from freezegun import freeze_time
from datetime import date, timedelta
from tests.types import Factory
from rest_framework.exceptions import NotFound
from billing.choices import BillingStatus as BS
from billing.models import BillingPeriod as BP
from billing import selectors as sl
from tenancy.models import Tenancy
from tenancy.choices import TenancyStatus as TS
from users.models import User


def test_number_of_queries(tenancy, django_assert_num_queries):
    """Accessing user data from the billing period should not result in a new query"""
    with django_assert_num_queries(1):
        bp = sl.BASE_QS.get(pk=1)
        assert bp.tenancy == tenancy
        assert bp.tenancy.user is not None
            

class TestBillingListFor:
    def test_role_based_filtering(self, superuser: User, manager_user: User, caretaker_user: User, tenancy_factory: Factory[Tenancy], billing_factory: Factory[BP]):
        """Test that the role based filtering works"""
        
        tset = tenancy_factory(2)
        bills_1 = billing_factory(quantity=2, tenancy=tset[0])
        bills_2 = billing_factory(quantity=3, tenancy=tset[1])
        total = sl.BASE_QS.all().count()
        assert sl.billing_list_for(user=superuser).count() == total
        assert sl.billing_list_for(user=manager_user).count() == total
        assert sl.billing_list_for(user=caretaker_user).count() == total
        fetched_1 = sl.billing_list_for(user=tset[0].user)
        assert {b.pk for b in bills_1} == set(fetched_1.values_list("pk", flat=True))
        fetched_2 = sl.billing_list_for(user=tset[1].user)
        assert {b.pk for b in bills_2} == set(fetched_2.values_list("pk", flat=True))

    
    def test_filtering_based_on_query_params(self, manager_user, user_factory, billing_factory, tenancy_factory, today):
        """
        Can filter correctly based on filters dict
        Should be able to filter based on status, is_current, period, search: "user_first_name", "user_last_name"
        """
        def query(filters: dict[str, str]):
            return sl.billing_list_for(user=manager_user, filters= filters)
        
        user1 = user_factory(first_name="John", last_name="Doe")
        user2 = user_factory(first_name="Alex", last_name="Smith")
        t = tenancy_factory(users=(user1+user2))
        
        billing_factory(tenancy=t[0], statuses=[BS.PAID, BS.CANCELED, BS.UNPAID], starting=date(2024, 1, 1))
        billing_factory(tenancy=t[1], statuses=[BS.CANCELED, BS.PAID], starting=date(2024, 2, 1))
        
        assert len(query({"status": "paid"})) == 2
        assert len(query({"status": "unpaid"})) == 1
        assert len(query({"period_after": "2024-1-1"})) == 5
        assert len(query({"period_after": "2024-2-1", "period_before": "2024-2-28"})) == 2
        assert len(query({"search": "Doe"})) == 3
        assert len(query({"search": "Ale"})) == 2
        
        with freeze_time("2024-2-1"):
            assert len(query({"is_current": "true"})) == 2



def test_billing_get_for_role_based_filtering(superuser: User, manager_user: User, caretaker_user: User, tenancy_factory: Factory[Tenancy], billing_factory: Factory[BP]):
    """Test that the role based filtering works"""
    
    tset = tenancy_factory(2)
    bills_1 = billing_factory(quantity=2, tenancy=tset[0])
    bills_2 = billing_factory(quantity=3, tenancy=tset[1])
    sl.billing_get_for(user=superuser, billing_id=bills_2[0].pk)
    sl.billing_get_for(user=manager_user, billing_id=bills_1[0].pk)
    sl.billing_get_for(user=caretaker_user, billing_id=bills_2[1].pk)
    fetched_1 = sl.billing_get_for(user=tset[0].user, billing_id=bills_1[0].pk)
    assert fetched_1 == bills_1[0]
    with pytest.raises(NotFound):
        sl.billing_get_for(user=tset[1].user, billing_id=bills_1[0].pk)


def test_billing_last_paid_for(tenancy_factory: Factory[Tenancy], billing_factory: Factory[BP]):
    """Raises if not found otherwise returns the last billing period"""
    t = tenancy_factory(2)
    billing_factory(tenancy=t[0], statuses=[BS.PAID, BS.PAID, BS.PAID], starting=date(2020, 1, 1))
    billing_factory(tenancy=t[1], statuses=[BS.CANCELED, BS.CANCELED, BS.UNPAID])

    last_paid = sl.billing_last_paid(t[0])
    # 1 Month each so the next billing is on the 1st of March
    assert last_paid.start_date == date(2020, 3, 1)

    with pytest.raises(NotFound):
        sl.billing_last_paid(t[1])
