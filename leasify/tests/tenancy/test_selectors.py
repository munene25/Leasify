import pytest
from datetime import date
from rest_framework.exceptions import NotFound
from leasify.tenancy.models import Tenancy
from leasify.tenancy import selectors as sl
from leasify.tenancy.choices import TenancyStatus as TS
from leasify.users.models import User
from leasify.apartments.models import Apartment
from leasify.tests.types import Factory
from leasify.apartments.choices import Block


class TestTenancyListFor:
    def test_filters_queryset_based_on_user_role(self, manager_user: User, caretaker_user: User, user: User, tenancy_factory: Factory[Tenancy]):
        """Managers and caretakers see all tenancies; tenants see only their own."""

        t1 = tenancy_factory()[0]
        t2 = tenancy_factory()[0]

        # Manager sees all
        manager_qs = sl.tenancy_list_for(user=manager_user)
        assert set(manager_qs) >= {t1, t2}

        # Caretaker sees all
        caretaker_qs = sl.tenancy_list_for(user=caretaker_user)
        assert set(caretaker_qs) >= {t1, t2}

        # Tenant sees only their own tenancy
        tenant_qs = sl.tenancy_list_for(user=t1.user)

        assert t1 in tenant_qs
        assert t2 not in tenant_qs

        # And vice versa
        tenant2_qs = sl.tenancy_list_for(user=t2.user)

        # For random user
        assert sl.tenancy_list_for(user=user).count() == 0 
        assert t2 in tenant2_qs
        assert t1 not in tenant2_qs

    def test_filters_based_on_query_filters(self, manager_user: User, tenancy_factory: Factory[Tenancy], user_factory: Factory[User], apartment_factory: Factory[Apartment], tenancy_patch_validators):
        """Query filters should filter down the Tenancy QuerySet based on inputs"""
        user1 = user_factory(first_name="John", last_name="Doe")
        user2 = user_factory(first_name="Alex", last_name="Smith")
        apartment1 = apartment_factory(block=Block.A, unit_number=101, rentable=True)
        apartment2 = apartment_factory(block=Block.B, unit_number=202, rentable=True)
        tenancy_factory(users=user1, apartments=apartment1, status=TS.TERMINATED, start_date=date(2026, 5, 1))
        tenancy_factory(users=user1, apartments=apartment1, status=TS.ACTIVE, start_date= date(2026, 7, 1))
        tenancy_factory(users=user2, apartments=apartment2, status=TS.ACTIVE, start_date= date(2026, 6, 1))

        def assert_query(q: dict[str, str | int], expected) -> None:
            qs = sl.tenancy_list_for(user=manager_user, filters=q)
            assert qs.count() == expected, f"Expected {expected} results {qs.all()}"

        # -- search on apartment --
        assert_query({"apartment": 2}, 1)
        # -- search on name --
        assert_query({"search": "John"}, 2)
        # -- search on block --
        assert_query({"block": Block.B}, 1)
        # -- search on status --
        assert_query({"status": TS.ACTIVE}, 2)
        # -- search on unit number --
        assert_query({"search": "101"}, 2)
        # -- search on partial last name --
        assert_query({"search": "Smi"}, 1)
        # -- search on dates --
        assert_query({"joined_after": "2026-06-01"}, 2)
        assert_query({"joined_after": "2026-06-01", "joined_before": "2026-06-30"}, 1)
        assert_query({"joined_before": "2026-5-30"}, 1)


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