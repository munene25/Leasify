from datetime import date
from tenancy.models import Tenancy
from tenancy.selectors import tenancy_list_for
from tenancy.choices import TenancyStatus as TS
from users.models import User
from apartments.models import Apartment
from tests.types import Factory

class TestTenancyListFilters:
    def test_tenancy_list_query_filters(self, manager_user: User, tenancy_factory: Factory[Tenancy], user_factory: Factory[User], apartment_factory: Factory[Apartment], tenancy_patch_validators):
        """
        Test that the query filters work as expected. We have a lot of them and they are important.
        """
        user1 = user_factory(first_name="John", last_name="Doe")
        user2 = user_factory(first_name="Alex", last_name="Smith")
        apartment1 = apartment_factory(block="NEW", unit_number="101", rentable=True)
        apartment2 = apartment_factory(block="OLD", unit_number="202", rentable=True)
        tenancy_factory(users=user1, apartments=apartment1, status=TS.TERMINATED, start_date=date(2026, 5, 1))
        tenancy_factory(users=user1, apartments=apartment1, status=TS.ACTIVE, start_date= date(2026, 7, 1))
        tenancy_factory(users=user2, apartments=apartment2, status=TS.ACTIVE, start_date= date(2026, 6, 1))

        def query(q: dict[str, str], expected) -> None:
            qs = tenancy_list_for(user=manager_user, filters=q)
            assert qs.count() == expected, f"Expected {expected} results {qs.all()}"

        # -- search on name --
        query({"search": "John"}, 2)
        # -- search on block --
        query({"search": "NEW"}, 2) # will show all tenancies with new block even duplicates.
        # -- search on status --
        query({"status": TS.ACTIVE}, 2)
        # -- search on unit number --
        query({"search": "101"}, 2)
        # -- search on partial last name --
        query({"search": "Smi"}, 1)
        # -- search on dates --
        query({"joined_after": "2026-06-01"}, 2)
        query({"joined_after": "2026-06-01", "joined_before": "2026-06-30"}, 1)
        query({"joined_before": "2026-5-30"}, 1)