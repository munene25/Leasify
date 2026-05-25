from apartments.selectors import *
from tenancy.services import tenancy_create
from apartments.models import Apartment
from tenancy.models import Tenancy
from common.period import DateRange
from django.utils import timezone

today = lambda: timezone.now().date()


class TestApartmentList:

    def test_apartment_for_regular_user(self, user_factory, apartment_factory, tenancy_validators_patch):
        """Test how Policy filters based on user"""
        apartments = apartment_factory(5, overrides={"rentable": True})
        users = user_factory(2)

        list_for_user1 = apartment_list_for(user=users[0], filters={})
        assert list_for_user1.count() == 5

        list_for_user2 = apartment_list_for(user=users[1], filters={})
        assert list_for_user2.count() == 5

        # Create a tenancy for user[0] last month and check list filtering again
        last_month = DateRange.for_month(today()).previous_month()
        t = tenancy_create(user=users[0], apartment=apartments[0], start_date=last_month.start_date, duration_months=2)

        # assert False
        list_2_for_user1 = apartment_list_for(user=users[0], filters={})
        assert list_2_for_user1.count() == 4
        list_2_for_user2 = apartment_list_for(user=users[1], filters={})
        assert list_2_for_user2.count() == 4
