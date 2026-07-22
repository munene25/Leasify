import pytest
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from tests.types import Factory
from apartments.models import Apartment
from apartments.choices import Block, Wing
from tenancy.models import Tenancy

class TestApartmentModel:
    # Test block and unit_number uniquess
    # Test Non nullable fields (Wing)
    # Test current_tenant property: number of queries
    # Test name formatting

    def test_constraints(self):
        apt1 = Apartment.objects.create(
            block=Block.A,
            unit_number=1,
            floor=0,
            rent=10_000,
            rentable=False,
            wing=Wing.WEST,
        )
        assert Apartment.objects.count() == 1
        with pytest.raises(IntegrityError):
            apt2 = Apartment.objects.create(
                block=Block.A,
                unit_number=1,
                floor=2,
                rent=20_000,
                rentable=True,
                wing=Wing.EAST,
            )
        assert Apartment.objects.count() == 1


    def test_non_nullable_fields(self):
        with pytest.raises(ValidationError, match="block"):
            apt = Apartment(floor=1, unit_number=1, rent=20_000, rentable=True)
            apt.full_clean()
            apt.save()

            
        with pytest.raises(ValidationError, match="unit_number"):
            apt = Apartment(floor=1, block=Block.A, rent=20_000, rentable=True)
            apt.full_clean()
            apt.save()

        with pytest.raises(ValidationError, match="rent"):
            apt = Apartment(block=Block.A, unit_number=1, floor=2, rentable=True)
            apt.full_clean()
            apt.save()

        # Wing can be ommitted
        apt = Apartment(
            block=Block.A,
            unit_number=1,
            floor=2,
            rent=20_000,
            rentable=True,
        )
        apt.full_clean()
        apt.save()
        assert Apartment.objects.count() == 1


    def test_name_formatting(self):
       
        apartment = Apartment.objects.create(
            block=Block.A,
            unit_number=7,
            rent=10_000,
            floor=2,
            wing=Wing.EAST,
        )

        assert apartment.name == "Unit A-207 | East wing"


    def test_model_propterties(self, tenancy_factory: Factory[Tenancy], django_assert_num_queries):

        from tenancy.selectors import CURRENT_TENANT

        apartment = Apartment.objects.create(
            block=Block.A,
            unit_number=7,
            rent=10_000,
            floor=2,
            wing=Wing.EAST,
        )
        apartment2 = Apartment.objects.create(
            block=Block.B,
            unit_number=7,
            rent=10_000,
            floor=2,
            wing=Wing.EAST,
        )
        tenant = tenancy_factory(apartments=[apartment])[0]

        with django_assert_num_queries(1):
            assert apartment.current_tenant == tenant

        apartment = Apartment.objects.prefetch_related(CURRENT_TENANT).get(pk=1)

        with django_assert_num_queries(0):
            assert apartment.current_tenant == tenant

        assert apartment.is_occupied == True

        assert apartment2.current_tenant is None
        assert apartment2.is_occupied is False
