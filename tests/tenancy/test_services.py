import pytest
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch
from django.contrib.auth.models import Group
from pytest_django import DjangoAssertNumQueries
from rest_framework.exceptions import ValidationError
from apartments.models import Apartment
from common.period import DateRange
from tests.types import Factory
from users.models import User
from users.services import user_set_role
from tenancy import validators as v
from tenancy.models import Tenancy, DEFAULT_RESERVATION_DURATION
from tenancy.choices import TenancyStatus, TerminationReason
from tenancy.selectors import tenancy_in
from apartments.selectors import apartment_lock
from billing.choices import BillingStatus
from tenancy.services import *
from billing.models import BillingPeriod
from users.models import User
from datetime import date
from apartments.models import Apartment


class TestTenancyCreation:
    
    def test_tenancy_creation_succeeds(self, user: User, today: date, apartment: Apartment):
        """
        This is technically the booking aspect of tenancy creation.
        A prospective tenant intends to stay in apartment x starts at time y for a duration z.
        At the end of the transaction, there should be a tenancy created in status reserved 
        and a billing period status unpaid.
        User is added to tenancy group.
        """

        duration_months = 2

        tenancy = tenancy_create(
            user=user, 
            apartment=apartment, 
            start_date=today, 
            duration_months=duration_months
        )

        assert tenancy == Tenancy.objects.first()
        assert tenancy.status == TenancyStatus.RESERVED
        assert tenancy.reservation_expiry == today + DEFAULT_RESERVATION_DURATION

        # In tenancy creation we only test that the tenancy was created and linked to the billing period.
        last_billing = BillingPeriod.objects.first()
        assert last_billing is not None
        assert last_billing.tenancy == tenancy
        assert last_billing.duration_months == duration_months
        
        assert user.groups.first() == Group.objects.filter(name="tenant").first()
    

    def test_tenancy_creation_calls_validators(self, user: User, today: date, apartment: Apartment, tenancy_patch_validators: dict[str, MagicMock]):
        """
        Instead of testing validation logic here, just mock they were called once with the arguments.
        """

        tenancy = tenancy_create(
            user=user,
            apartment=apartment,
            start_date=today,
            duration_months=1
        )

        validate_reservations = tenancy_patch_validators["user_reservations"]
        validate_lease_period = tenancy_patch_validators["lease_period"]
        validate_reservations.assert_called_once_with(user.pk)
        validate_lease_period.assert_called_once_with(today)
    
    def test_tenancy_creation_fails_for_non_rentable_apartment(self, user: User, apartment: Apartment, today: date):
        """
        Set apartment to not rented and expect validation error
        """
        apartment.rentable = False
        apartment.save()
        with pytest.raises(ApartmentUnavailableError) as exc:
            tenancy_create(
                user=user,
                apartment=apartment,
                start_date=today,
                duration_months=1
            )
        assert Tenancy.objects.count() == 0

    def test_model_constraints_fail_on_conflicts(self, user_factory: Factory[User],apartment_factory: Factory[Apartment],today: date, tenancy_patch_validators: dict[str, MagicMock]):
        """
        The same apartment should not exist in states [defaulting, active reserved]
        The same user should not exist in the states [defaulting, active, reserved]
        """
        apt1, apt2 = apartment_factory(2, overrides={"rentable": True})
        user1, user2 = user_factory(2)
        r = DateRange.for_month(today)
        
        next_month = r.next_month()
        last_month = r.previous_month()

        # first create a reservation for user1
        first_tenancy = tenancy_create(
            user=user1,
            apartment=apt1,
            start_date=today,
            duration_months=1
        )
        # Full clean raises drf validation errors coerced from BaseModel.
        # Try create a new tenancy with the same user in a new apartment
        with pytest.raises(ValidationError) as exc:
            tenancy_create(
                user=user1,
                apartment=apt2,
                start_date=next_month.start_date,
                duration_months=1
            )
        assert "This Aparment or User is already associated with a tenancy" in str(exc.value.detail)


        # Try create a tenancy with a different user on the same apartment
        with pytest.raises(ValidationError) as exc:
            tenancy_create(
                user=user2,
                apartment=apt1,
                duration_months=1,
                start_date=last_month.start_date
            )
        assert "This Aparment or User is already associated with a tenancy" in str(exc.value.detail)
    

    def test_tenancy_creation_no_queries(self, today: date, user: User, apartment: Apartment, django_assert_num_queries: DjangoAssertNumQueries):
        """
        1. transaction open
        2. monthly reservations for user
        3. aparment locking
        4. check tenancy constraint
        5. create tenant
        6. check tenant group exists
        7. get tenant group
        8. add group to tenant
        9. check constraints via 
        10. create billing period
        11. transaction close
        """

        assert user is not None
        assert apartment is not None

        with django_assert_num_queries(11):
            tenancy_create(
                user=user,
                duration_months=1,
                apartment=apartment,
                start_date=today,
            )

class TestTenancyLeaseExtension:
    def test_tenancy_lease_extension_successful(self):
        ...