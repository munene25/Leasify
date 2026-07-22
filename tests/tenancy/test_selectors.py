import pytest
from datetime import date
from rest_framework.exceptions import NotFound
from tenancy.models import Tenancy
from tenancy import selectors as sl
from tenancy.choices import TenancyStatus as TS
from users.models import User
from apartments.models import Apartment
from tests.types import Factory
from apartments.choices import Block


def test_tenancy_list_for_query_filters(manager_user: User, tenancy_factory: Factory[Tenancy], user_factory: Factory[User], apartment_factory: Factory[Apartment], tenancy_patch_validators):
        """
        Test that the query filters work as expected.
        """
        user1 = user_factory(first_name="John", last_name="Doe")
        user2 = user_factory(first_name="Alex", last_name="Smith")
        apartment1 = apartment_factory(block=Block.A, unit_number=101, rentable=True)
        apartment2 = apartment_factory(block=Block.B, unit_number=202, rentable=True)
        tenancy_factory(users=user1, apartments=apartment1, status=TS.TERMINATED, start_date=date(2026, 5, 1))
        tenancy_factory(users=user1, apartments=apartment1, status=TS.ACTIVE, start_date= date(2026, 7, 1))
        tenancy_factory(users=user2, apartments=apartment2, status=TS.ACTIVE, start_date= date(2026, 6, 1))

        def query(q: dict[str, str | int], expected) -> None:
            qs = sl.tenancy_list_for(user=manager_user, filters=q)
            assert qs.count() == expected, f"Expected {expected} results {qs.all()}"

        # -- search on apartment --
        query({"apartment": 2}, 1)
        # -- search on name --
        query({"search": "John"}, 2)
        # -- search on block --
        query({"search": Block.B}, 1) # will show all tenancies with new block even duplicates.
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


class TestTenancyGetFor:
    def test_filters_based_on_user_roles(self, manager_user: User, caretaker_user: User, user: User, tenancy_factory: Factory[Tenancy]):
        """Manager, caretaker, and the owning tenant should access the tenancy."""

        t1 = tenancy_factory()[0]
        t2 = tenancy_factory()[0]

        assert sl.tenancy_get_for(manager_user, t1.pk) == t1
        assert sl.tenancy_get_for(caretaker_user, t2.pk) == t2

        assert sl.tenancy_get_for(t1.user, t1.pk) == t1
        assert sl.tenancy_get_for(t2.user, t2.pk) == t2

        with pytest.raises(NotFound):
            sl.tenancy_get_for(t2.user, t1.pk)

        with pytest.raises(NotFound):
            sl.tenancy_get_for(t1.user, t2.pk)

        with pytest.raises(NotFound):
            sl.tenancy_get_for(user, t2.pk)


    def test_raises_not_found_for_unauthorized_user(self, user_factory: Factory[User], tenancy_factory: Factory[Tenancy]):
        """A user without the required role should not access the tenancy."""

        tenancy = tenancy_factory()[0]
        random_user = user_factory()[0]

        with pytest.raises(NotFound):
            sl.tenancy_get_for(random_user, tenancy.pk)

    def test_raises_not_found_for_nonexistent_tenancy(self, manager_user: User):
        """A nonexistent tenancy ID should raise NotFound."""

        with pytest.raises(NotFound):
            sl.tenancy_get_for(manager_user, 999999)