import pytest
from decimal import Decimal
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from tests.types import Factory
from apartments.models import Apartment
from apartments.choices import Block, Wing
from tenancy.models import Tenancy
from tenancy.choices import TenancyStatus as TS

class TestApartmentModel:
    def test_constraints(self):
        """Verify unique together constraint on block and unit_number"""

        apt1 = Apartment.objects.create(
            block=Block.A,
            unit_number=1,
            floor=0,
            rent=10_000,
            rentable=True,
            wing=Wing.WEST,
        )
        assert Apartment.objects.count() == 1

        apt1.refresh_from_db()

        assert apt1.block == "A"
        assert apt1.unit_number == 1
        assert apt1.floor == 0
        assert apt1.rent == Decimal(10_000)
        assert apt1.rentable == True
        assert apt1.wing == "west"

        with pytest.raises(IntegrityError):
            Apartment.objects.create(
                block=apt1.block,
                unit_number=apt1.unit_number,
                floor=2,
                rent=20_000,
                rentable=False,
                wing=Wing.EAST,
            )
        assert Apartment.objects.count() == 1


    @pytest.mark.parametrize("field", ["unit_number", "floor", "block", "rent"])
    def test_non_nullable_fields(self, apartment_data: dict, field: str):
        """Block, unit_number, floor, rent, rentable should raise validation error if ommited """

        apartment_data.pop(field)
        with pytest.raises(ValidationError, match=field):
            apartment = Apartment(**apartment_data)
            apartment.full_clean()
            apartment.save()


    def test_name_formatting(self):
        """Verify apartment name property returns correctly formatted string with block, floor, wing and unit."""

        apartment = Apartment.objects.create(
            block=Block.A,
            unit_number=7,
            rent=10_000,
            floor=2,
            wing=Wing.EAST,
        )

        assert apartment.name == "Unit A-207 | East wing"


    def test_occupancy_query_count(self, apartment_factory: Factory[Apartment], tenancy_factory: Factory[Tenancy], django_assert_num_queries):
        """Querying for current tenant and is_occupied should not result in further queries if adequately prefetched"""

        from tenancy.selectors import CURRENT_TENANT

        apartment = apartment_factory()[0]
        tenant = tenancy_factory(apartments=[apartment])[0]

        with django_assert_num_queries(2):
            assert apartment.current_tenant == tenant
            assert apartment.is_occupied == True

        apartment = Apartment.objects.prefetch_related(CURRENT_TENANT).get(pk=apartment.pk)

        with django_assert_num_queries(0):
            assert apartment.current_tenant == tenant
            assert apartment.is_occupied == True

    @pytest.mark.parametrize(
        "tenancy_status,occupied",
        [
            (TS.ACTIVE, True), 
            (TS.RESERVED, True),
            (TS.DEFAULTING, True),
            (TS.TERMINATED, False),
        ]
    )
    def test_occupancy_dependent_on_tenancy(self, tenancy_status: str, occupied: bool, tenancy_factory: Factory[Tenancy]):
        """The occupancy depends on the occupying tenant status"""
        tenant = tenancy_factory(status=tenancy_status)[0]
        apartment = tenant.apartment
        assert apartment.is_occupied == occupied, str(apartment.current_tenant)
        assert apartment.current_tenant == tenant if occupied else True