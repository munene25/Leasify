from apartments.selectors import *
from tenancy.services import tenancy_create
from apartments.models import Apartment
from tenancy.models import Tenancy
from common.period import DateRange
from django.utils import timezone

today = lambda: timezone.now().date()

class TestApartmentList:

    def test_apartment_for_regular_user(self, user_factory, apartment_factory, tenancy_patch_validators):
        """Test how Policy filters based on user"""
        apartments = apartment_factory(5, rentable=True)
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
        
    
    def test_apartment_filters_based_on_filters(self, manager_user, apartment_factory):
        """test that apartments can be filtered based on "rentable" or "search" params"""

        apartment_factory(block="OLD", unit_number=1, rentable=True, rent=12000)
        apartment_factory(block="NEW", unit_number=2, rentable=True, rent=15000)
        apartment_factory(block="OLD", unit_number=3, rentable=False, rent=20000)
        
        # test that "rentable" filter works
        assert apartment_list_for(user=manager_user, filters={"rentable": True}).count() == 2
        assert apartment_list_for(user=manager_user, filters={"rentable": False}).count() == 1

        # test that "search" filter works
        assert apartment_list_for(user=manager_user, filters={"search": "OLD"}).count() == 2
        assert apartment_list_for(user=manager_user, filters={"search": "NEW"}).count() == 1

        # test "search" and "rentable" works together
        apt = apartment_list_for(user=manager_user, filters={"search": "OLD", "rentable": False})
        assert apt.latest("pk").pk == 3

        # test "unit number" search works
        apt = apartment_list_for(user=manager_user, filters={"search": "3"})
        assert apt.latest("pk").unit_number == 3

        # test "rent" works
        assert apartment_list_for(user=manager_user, filters={"rent_min": 20000}).count() == 1
        