import pytest
from unittest.mock import MagicMock
from pytest_django import DjangoAssertNumQueries
from rest_framework.exceptions import ValidationError, NotFound
from apartments.models import Apartment
from common.period import DateRange, today as _today
from tests.types import Factory, TenancyPayload
from tenancy.models import Tenancy, DEFAULT_RESERVATION_DURATION
from tenancy.choices import TenancyStatus, TerminationReason
from billing.choices import BillingStatus
from users.models import User
from users.selectors import get_group
from tenancy.services import *
from billing.models import BillingPeriod
from datetime import date, timedelta
from apartments.models import Apartment
from datetime import timedelta


class TestTenancyCreation:

    def test_tenancy_creation_succeeds(self, tenancy_payload: TenancyPayload, today: date):
        """
        This is technically the booking aspect of tenancy creation.
        A prospective tenant intends to stay in apartment x starts at time y for a duration z.
        At the end of the transaction, there should be a tenancy created in status reserved
        and a billing period status unpaid.
        User is added to tenancy group.
        """

        user = tenancy_payload["user"]
        tenancy = tenancy_create(**tenancy_payload)
        tenancy.refresh_from_db()

        assert tenancy == Tenancy.objects.first()
        assert tenancy.status == TenancyStatus.RESERVED
        assert tenancy.reservation_expiry == today + DEFAULT_RESERVATION_DURATION
        assert tenancy.date_joined == today

        # In tenancy creation we only test that the tenancy was created and linked to the billing period.
        last_billing = BillingPeriod.objects.first()
        assert last_billing is not None
        assert last_billing.tenancy == tenancy
        assert user.groups.first() == get_group("tenant")

    @pytest.mark.parametrize(
        "duration_months", 
        [1, 2, 3, 4]
    )    
    def test_tenancy_creation_calls_billing_period_with_correct_arguments(self, tenancy_payload: TenancyPayload, duration_months: int, tenancy_patch_validators: dict[str, MagicMock], mock_billing_create: MagicMock):
        """This is in order to avoid testing billing period in tenancy"""

        tenancy_payload["duration_months"] = duration_months
        t = tenancy_create(**tenancy_payload)

        date_range = DateRange.for_month().shift_months(0, + (duration_months-1))
        mock_billing_create.assert_called_once_with(tenancy=t, date_r=date_range)

    def test_tenancy_creation_calls_validators(self, tenancy_payload: TenancyPayload, today: date, tenancy_patch_validators: dict[str, MagicMock]):
        """
        Instead of testing validation logic here, just mock they were called once with the arguments.
        """

        user = tenancy_payload["user"]
        tenancy_create(**tenancy_payload)

        validate_reservations = tenancy_patch_validators["user_reservations"]
        validate_lease_period = tenancy_patch_validators["lease_period"]
        validate_reservations.assert_called_once_with(user.pk)
        validate_lease_period.assert_called_once_with(today)

    def test_tenancy_creation_fails_for_non_rentable_apartment(self, tenancy_payload: TenancyPayload):
        """
        Set apartment to not rented and expect validation error
        """
        tenancy_payload["apartment"].rentable = False
        tenancy_payload["apartment"].save()
        with pytest.raises(ApartmentUnavailableError) as exc:
            tenancy_create(**tenancy_payload)
        assert Tenancy.objects.count() == 0

    def test_model_constraints_fail_on_conflicts(self, user_factory: Factory[User], apartment_factory: Factory[Apartment], today: date, tenancy_patch_validators: dict[str, MagicMock],):
        """
        The same apartment should not exist in states [defaulting, active reserved]
        The same user should not exist in the states [defaulting, active, reserved]
        """
        a1, a2 = apartment_factory(2, rentable=True)
        u1, u2 = user_factory(2)
        r = DateRange.for_month(today)

        next_month = r.next_month()
        last_month = r.previous_month()

        # first create a reservation for user1
        first_tenancy = tenancy_create(user=u1, apartment=a1, start_date=today, duration_months=1)

        # Full clean raises drf validation errors coerced from BaseModel.
        # Try create a new tenancy with the same user in a new apartment
        with pytest.raises(ValidationError) as exc:
            tenancy_create(user=u1, apartment=a2, start_date=next_month.start_date, duration_months=1)

        assert "This Aparment or User is already associated with a tenancy" in str(exc.value.detail)

        # Try create a tenancy with a different user on the same apartment
        with pytest.raises(ValidationError) as exc:
            tenancy_create(user=u2, apartment=a1, duration_months=1, start_date=last_month.start_date)

        assert "This Aparment or User is already associated with a tenancy" in str(exc.value.detail)

    def test_tenancy_creation_no_queries(
        self, tenancy_payload: TenancyPayload, django_assert_num_queries: DjangoAssertNumQueries
    ):
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
        # ! This is cut down to 10 in most cases coz of the lru cache, it ommits getting the tenancy group.
        with django_assert_num_queries(10):
            tenancy_create(**tenancy_payload)

    @pytest.mark.parametrize("_user", ("manager_user", "caretaker_user"))
    def test_tenancy_creation_fails_for_priviledged_users(self, _user: str, request: pytest.FixtureRequest, tenancy_payload: TenancyPayload):
        """For manager and caretaker clients, it should raise RoleAssigmentError in service"""
        from common.exceptions import RoleAssignmentError

        user = request.getfixturevalue(_user)
        tenancy_payload["user"] = user
        with pytest.raises(RoleAssignmentError):
            tenancy_create(**tenancy_payload)

class TestTenancyLeaseExtension:
    def test_tenancy_lease_extension_successful(self, active_tenant: Tenancy, today: date):
        """
        This can only work if the tenant has actually made a payment and they are active or defaulting.
        We can just ignore that by making the billing period paid.
        """

        # now extending should work
        tenancy = tenancy_lease_extend(active_tenant, 1)[0]
        tenancy.refresh_from_db()
        assert tenancy == active_tenant
        assert tenancy.billings.count() == 2

    @pytest.mark.parametrize(
        "duration_months",
        [1, 2, 3, 4]
    )
    def test_tenancy_lease_extension_calls_billing_period_with_correct_args(self, monkeypatch: pytest.MonkeyPatch, duration_months: int, active_tenant: Tenancy, mock_billing_create: MagicMock):
        """billing period should be called with the new date range computed from """
        

        monkeypatch.setattr(Tenancy, "is_continuing", property(lambda self: True))
        monkeypatch.setattr(Tenancy, "has_pending_bills", property(lambda self: False))

        tenancy_lease_extend(active_tenant, duration_months)
        # today is implied
        r = DateRange.for_month().shift_months(1, duration_months)
        mock_billing_create.assert_called_once_with(tenancy=active_tenant, date_r=r)


    @pytest.mark.parametrize(
        "status",
        [
            TenancyStatus.RESERVED,
            TenancyStatus.TERMINATED,
        ],
    )
    def test_lease_extension_fails_for_terminated_or_reserved(self, tenancy: Tenancy, status: TenancyStatus):
        """
        Change tenancy status and try to extend. Expect error
        """
        tenancy.status = status
        tenancy.save(update_fields=["status"])

        with pytest.raises(ValidationError) as exc:
            tenancy_lease_extend(tenancy, 1)
        assert "Only continuing tenants can extend their lease" in str(exc.value.detail)



    def test_lease_extension_fails_for_unpaid_billings(self, tenancy_factory: Factory[Tenancy]):
        """Since a new tenant already has a unpaid billing period, we just have to patch their status"""
        tenant = tenancy_factory(status=TenancyStatus.ACTIVE)[0]
        tenant.billings.update(status=BillingStatus.UNPAID)
        with pytest.raises(ValidationError) as exc:
            tenancy_lease_extend(tenant, 1)

        assert "You have an unpaid billing period" in str(exc.value.detail)

    
    def test_edge_case_no_last_paid_billing(self, active_tenant: Tenancy):
        """Tenant canceled their one and only billing, should raise a not found"""
        
        active_tenant.status = TenancyStatus.ACTIVE
        last_billing = active_tenant.billings.update(status=BillingStatus.CANCELED)

        with pytest.raises(NotFound) as exc:
            tenancy_lease_extend(active_tenant, duration_months=1)
        assert "No paid billing exists" in str(exc.value.detail)
    

    def test_lease_extend_no_queries(self, active_tenant: Tenancy, monkeypatch: pytest.MonkeyPatch, django_assert_num_queries: DjangoAssertNumQueries):
        """
        1. transaction start
        2. lock tenancy
        3. check pending bills
        4. get last paid billing
        5. create billing period
        6. transaction end
        """
        monkeypatch.setattr(Tenancy, "is_continuing", property(lambda self: True))
        with django_assert_num_queries(6):
            tenancy_lease_extend(active_tenant, 1)
        

class TestTenancyTerminate:

    @pytest.mark.parametrize(
            "date,reason",
            [
                (_today(), TerminationReason.VOLUNTARY),
                (_today() + timedelta(days=1), TerminationReason.MANAGERIAL),
                (_today() + timedelta(days=30), TerminationReason.EXPIRED),
                (None, TerminationReason.NONPAYMENT),
            ]
    )
    def test_tenancy_termination_successful(self, reserved_tenant: Tenancy, date: date, reason: TerminationReason, today: date):
        """
        Termination_date, termination_reason and status should be updated.
        Unpaid billing periods are cancelled
        """
        t = tenancy_terminate(tenancy=reserved_tenant, termination_date=date, termination_reason=reason)
        t.refresh_from_db()
        assert t == reserved_tenant
        assert t.status == TenancyStatus.TERMINATED
        assert t.termination_date == date or today
        assert t.termination_reason == reason

        billing = t.billings.latest("start_date")
        assert billing.status == BillingStatus.CANCELED
 
    
    def test_tenancy_termination_fails_for_backdated_termination_dates(self, tenancy: Tenancy, today: date):
        with pytest.raises(ValidationError) as exc:
            tenancy_terminate(
                tenancy=tenancy, 
                termination_reason=TerminationReason.VOLUNTARY, 
                termination_date=today-timedelta(days=1)
            )
        assert "Cannot set termination date before tenant's creation" in str(exc.value.detail)
    
    def test_tenancy_termination_does_not_close_paid_billings(self, active_tenant):
        """Paid billings should remain untouched"""
        t = tenancy_terminate(tenancy=active_tenant, termination_reason=TerminationReason.VOLUNTARY)
        t.refresh_from_db()
        assert t.billings.filter(status=BillingStatus.CANCELED).count() == 0