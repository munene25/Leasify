import pytest
from leasify.tenancy.models import Tenancy
from leasify.tenancy.validators import *
from leasify.tenancy.choices import TenancyStatus
from leasify.tests.types import Factory
from leasify.users.models import User
from freezegun import freeze_time


class TestMaxMonthlyReservations:
    def test_with_one_reserved_fails(self, user_factory: Factory[User], tenancy_factory: Factory[Tenancy]):
        """In the case of one reserved tenancy should fail"""
    
        user1 = user_factory()
        tenancy_factory(users=user1, status=TenancyStatus.RESERVED)
        with pytest.raises(MaxReservationsExceededError):
            validate_max_monthly_reservations(user_id=user1[0].pk)

    def test_with_two_terminated_fails(self, user_factory: Factory[User], tenancy_factory: Factory[Tenancy]):
        """In the case of two terminated tenancies should fail"""
        users = user_factory()
        tenancy_factory(2, users=[users[0], users[0]], status=TenancyStatus.TERMINATED)
        with pytest.raises(MaxReservationsExceededError):
            validate_max_monthly_reservations(user_id=users[0].pk)


    def test_with_one_terminated_succeeds(self, tenancy_factory: Factory[Tenancy]):
        """In the case of one terminated tenancy should succeed """
        tenancy_factory(status=TenancyStatus.TERMINATED)
        # Should not raise
        validate_max_monthly_reservations(user_id=1)

class TestLeasePeriod:
    def test_with_current_month_succeeds(self):
        """This month should always work"""
        with freeze_time("2024-06-15"):
            validate_lease_period(date(2024, 6, 20))
    
    def test_with_next_month_succeeds(self):
        """Next month should work from 21st moving forward"""
        with freeze_time("2024-06-21"):
            validate_lease_period(date(2024, 7, 20))

    def test_with_next_month_before_21st_fails(self):
        """Next month should not work before the 21st of the month"""
        with freeze_time("2024-06-20"):
            with pytest.raises(ValidationError):
                validate_lease_period(date(2024, 7, 20))