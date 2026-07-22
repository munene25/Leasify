import pytest
from decimal import Decimal
from tests.types import Factory
from rest_framework.exceptions import NotFound
from users.models import User
from apartments import selectors as sl, choices as ch
from tenancy.models import Tenancy
from apartments.models import Apartment
from tenancy.choices import TenancyStatus as TS


class TestApartmentListFor:
    def test_list_filters_based_on_role(
        self,
        superuser: User,
        manager_user: User,
        caretaker_user: User,
        tenant_user: User,
        user: User,
        apartment_factory: Factory[Apartment],
        tenancy_factory: Factory[Tenancy],
    ):
        """The apartment list will based on role"""
        rentable = apartment_factory(rentable=True, quantity=2)
        tenancy = tenancy_factory(apartments=[rentable[0]])[0]
        apartment_factory(rentable=False, quantity=1)

        def assert_query(u: User, count: int):
            qs = sl.apartment_list_for(user=u)
            assert qs.count() == count

        assert_query(superuser, 3)
        assert_query(manager_user, 3)
        assert_query(caretaker_user, 3)
        assert_query(tenant_user, 1)
        assert_query(user, 1)
        tenancy.status = "terminated"
        tenancy.save()

        assert_query(tenant_user, 2)
        assert_query(user, 2)

    def test_query_based_filtering(self, manager_user: User, apartment_factory: Factory[Apartment]):
        """Given a number of apartments, we should be able to filter out the specific ones"""
        first = apartment_factory(rent=10_000, floor=1, unit_number=7, block=ch.Block.A, wing=ch.Wing.EAST)[0]
        second = apartment_factory(rent=10_000, floor=2, unit_number=8, block=ch.Block.A, wing=ch.Wing.WEST)[0]
        third = apartment_factory(rent=20_000, floor=0, unit_number=7, block=ch.Block.B, wing=ch.Wing.NORTH)[0]
        fourth = apartment_factory(rent=30_000, floor=3, unit_number=7, block=ch.Block.C, wing=ch.Wing.SOUTH)[0]

        def assert_query(filters: dict, count: int, apt: Apartment | None):
            qs = sl.apartment_list_for(user=manager_user, filters=filters)
            assert qs.count() == count
            assert apt in qs if apt else True

        assert_query({"rent_max": 10_000}, 2, first)
        assert_query({"rent_max": 10_000, "floor": 2}, 1, second)
        assert_query({"rent_min": 30_000}, 1, fourth)
        assert_query({"floor": 3}, 1, fourth)
        assert_query({"unit_number": 7}, 3, third)
        assert_query({"unit_number": 7, "block": ch.Block.B}, 1, third)
        assert_query({"unit_number": 7, "block": ch.Block.C, "wing": ch.Wing.SOUTH}, 1, fourth)
        assert_query({"unit_number": 8, "floor": 1}, 0, None)


class TestApartmentGetOverview:
    def test_returns_correct_overview_statistics(self, apartment_factory: Factory[Apartment], tenancy_factory: Factory[Tenancy],):
        """The overview selector should return correct aggregate statistics."""

        # Create apartments
        a1 = apartment_factory(rent=Decimal("10000.00"), rentable=True, block=ch.Block.A, unit_number=101,)[0]

        a2 = apartment_factory(rent=Decimal("20000.00"), rentable=True, block=ch.Block.B, unit_number=202,)[0]

        a3 = apartment_factory(rent=Decimal("30000.00"), rentable=False, block=ch.Block.C, unit_number=303,)[0]

        # Create tenancy history / occupancy
        tenancy_factory(apartments=[a1, a1], status=TS.ACTIVE)
        tenancy_factory(apartments=[a2], status=TS.DEFAULTING)

        overview = sl.apartment_get_overview()

        # Counts
        assert overview["total_apartments"] == 3
        assert overview["rentable"] == 2
        assert overview["occupied"] == 2  # a1 and a2

        # Rent aggregates
        assert overview["average_rent"] == Decimal("20000.00")
        assert overview["min_rent"] == Decimal("10000.00")
        assert overview["max_rent"] == Decimal("30000.00")

        # Only rentable apartments contribute
        assert overview["gross_expected"] == Decimal("30000.00")

        # Popularity (a1 has 2 tenancies, others have <= 1)
        assert overview["most_popular"] == a1.name

        # Least popular should be one of the apartments with the fewest tenancies
        assert overview["least_popular"] in {a2.name, a3.name}


class TestApartmentGetFor:
    def test_filters_based_on_user_roles(
        self,
        superuser: User,
        manager_user: User,
        caretaker_user: User,
        tenant_user: User,
        user: User,
        apartment_factory: Factory[Apartment],
        tenancy_factory: Factory[Tenancy],
    ):
        """The selector should return apartments visible to the requesting role."""

        visible = apartment_factory(rentable=True)[0]
        hidden = apartment_factory(rentable=False)[0]

        # Administrative roles can access any apartment
        assert sl.apartment_get_for(user=superuser, apartment_id=visible.pk) == visible
        assert sl.apartment_get_for(user=superuser, apartment_id=hidden.pk) == hidden

        assert sl.apartment_get_for(user=manager_user, apartment_id=visible.pk) == visible
        assert sl.apartment_get_for(user=manager_user, apartment_id=hidden.pk) == hidden

        assert sl.apartment_get_for(user=caretaker_user, apartment_id=visible.pk) == visible
        assert sl.apartment_get_for(user=caretaker_user, apartment_id=hidden.pk) == hidden

        assert sl.apartment_get_for(user=tenant_user, apartment_id=visible.pk) == visible

        with pytest.raises(NotFound):
            assert sl.apartment_get_for(user=tenant_user, apartment_id=hidden.pk) == hidden

        assert sl.apartment_get_for(user=user, apartment_id=visible.pk) == visible

        with pytest.raises(NotFound):
            sl.apartment_get_for(user=user, apartment_id=hidden.pk)

    def test_raises_not_found(self, manager_user: User,):
        """A nonexistent apartment ID should raise NotFound."""

        with pytest.raises(NotFound):
            sl.apartment_get_for(user=manager_user, apartment_id=999999)