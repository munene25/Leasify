import pytest
import typing
from unittest.mock import MagicMock
from tests.types import Factory
from faker import Faker
from django.core.management import call_command
from django.contrib.auth.models import Group
from users.models import User
from users.services import user_account_create, user_set_role
from rest_framework.test import APIClient
from django.core.cache import cache
from apartments.services import apartment_create
from apartments.models import Apartment
from tenancy.models import Tenancy
from datetime import date, timedelta

# ------------------------------------------------------ Globals  ------------------------------------------------------ #

# # conftest.py
# import warnings


# def pytest_configure(config):
#     warnings.filterwarnings("error", category=RuntimeWarning)


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "fixtures/roles.json")


@pytest.fixture
def override_pagination():
    from rest_framework.pagination import PageNumberPagination

    test_page_size = 2

    original_page_size = PageNumberPagination.page_size
    PageNumberPagination.page_size = test_page_size

    yield test_page_size

    PageNumberPagination.page_size = original_page_size


@pytest.fixture
def override_throttles():
    from rest_framework.throttling import SimpleRateThrottle

    update = lambda d: {k: "1/min" for k, v in d.items()}
    original_rates = SimpleRateThrottle.THROTTLE_RATES
    SimpleRateThrottle.THROTTLE_RATES = update(original_rates)
    yield

    SimpleRateThrottle.THROTTLE_RATES = original_rates
    # Cache clearing in a seperate fixture


@pytest.fixture(autouse=True)
def enable_db_access(db):
    """Automatically enable db access for all tests."""
    pass


@pytest.fixture(scope="function")
def cache_clear():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def settings_override(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.LOGGING = None
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }


@pytest.fixture
def fake():
    """
    Return a faker instance with a locale already set
    """

    return Faker("en_KE")


@pytest.fixture
def today():
    "Returns today's date"
    from django.utils import timezone

    return timezone.now().date()


# ------------------------------------------------------ Users  ------------------------------------------------------ #


@pytest.fixture
def user_factory(fake, phone_no) -> Factory[User]:
    """Returns a callable for generating users"""

    def create(quantity: int = 1, overrides: dict[str, typing.Any] = {}) -> list[User]:
        users = []
        for _ in range(quantity):
            users.append(
                user_account_create(
                    first_name=(overrides.get("fist_name", fake.first_name())),
                    last_name=overrides.get("last_name", fake.last_name()),
                    password="Pa55word!",
                    email=overrides.get("email", fake.email()),
                    phone_number=overrides.get("phone_number", phone_no()),
                    notify=False,
                )
            )
        return users

    return create


@pytest.fixture
def user(user_factory) -> User:
    return user_factory()[0]


@pytest.fixture
def roles_list() -> list[Group]:
    """
    Returns a list of all available roles|Groups
    """
    return list(Group.objects.all())


@pytest.fixture
def get_role() -> typing.Callable[[str], Group]:
    """
    Callable to return a specific group
    Pass in the str value of the group
    """
    from users.selectors import get_group
    return lambda name: get_group(name)


@pytest.fixture
def super_user(user_factory):
    u: User = user_factory()[0]
    u.is_superuser = True
    u.save(update_fields=["is_superuser"])
    return u


@pytest.fixture
def manager_user(user_factory, get_role) -> User:
    u = user_factory()[0]
    user_set_role(user=u, role=get_role("manager"))
    return u


@pytest.fixture
def caretaker_user(user_factory, get_role) -> User:
    u = user_factory()[0]
    user_set_role(user=u, role=get_role("caretaker"))
    return u


@pytest.fixture
def tenant_user(user_factory, get_role) -> User:
    u = user_factory()[0]
    user_set_role(user=u, role=get_role("tenant"))
    return u


@pytest.fixture
def password() -> str:
    """Default password for test users"""
    return "Pa55word!"


@pytest.fixture
def phone_no(fake) -> typing.Callable[[],str]:
    return lambda: fake.numerify("2547########")


# ------------------------------------------------------ API clients  ------------------------------------------------------ #


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def csrf_client() -> APIClient:
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def user_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def manager_client(manager_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=manager_user)
    return client


@pytest.fixture
def tenant_client(tenant_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=tenant_user)
    return client


@pytest.fixture
def caretaker_client(caretaker_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=caretaker_user)
    return client


@pytest.fixture
def super_user_client(super_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=super_user)
    return client


# ------------------------------------------------ Apartments  ------------------------------------------------


@pytest.fixture
def apartment_factory(fake) -> Factory[Apartment]:
    """Returns a callable for generating apartments"""

    def create(quantity: int = 1, overrides: dict[str, typing.Any] = {}, ordered: bool = False):
        import random
        from decimal import Decimal

        apartments: list[Apartment] = []
        for i in range(quantity):
            apt = apartment_create(
                block=overrides.get("block", random.choice(Apartment.Block.values)),
                unit_number=(i + 1) if ordered else overrides.get("unit_number", int(fake.building_number())),
                rent=overrides.get("rent", Decimal(fake.numerify("1#000"))),
                rentable=overrides.get("rentable", random.choice((True, False))),
            )
            apartments.append(apt)
        return apartments

    return create


@pytest.fixture
def apartment(apartment_factory) -> Apartment:
    return apartment_factory(ordered=True, overrides={"block": "NEW", "rent": 20_000, "rentable": True})[0]


# ------------------------------------------------ Tenancy  ------------------------------------------------
@pytest.fixture
def tenancy_patch_validators(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    user_reservations = MagicMock()
    lease_period = MagicMock()
    
    monkeypatch.setattr("tenancy.validators.validate_max_monthly_reservations", user_reservations)
    monkeypatch.setattr("tenancy.validators.validate_lease_period", lease_period)

    return {"user_reservations": user_reservations,"lease_period": lease_period}


@pytest.fixture
def tenancy_factory(apartment_factory, user_factory, today) -> Factory[Tenancy]:
    """Tenancy generator - creates lease-based tenancies"""
    from tenancy.services import tenancy_create
    from tenancy.choices import TenancyStatus

    def create(
        quantity=1,
        users: list[User] | None = None,
        apartments: list[Apartment] | None = None,
        overrides: dict[str, typing.Any] = {},
    ) -> list[Tenancy]:
        tenancies = []

        users = users or user_factory(quantity)
        apartments = apartments or apartment_factory(quantity)

        duration_months = overrides.get("duration_months", 1)
        start_date: date = overrides.get("start_date", today)
        status = overrides.get("status", TenancyStatus.ACTIVE)

        for i, user in enumerate(users):
            tenancy = tenancy_create(
                user=user,
                apartment=apartments[i],
                start_date=start_date,
                duration_months=duration_months,
            )
            if status != tenancy.status:
                tenancy.status = status
                tenancy.save()

            tenancies.append(tenancy)

        return tenancies

    return create


@pytest.fixture
def tenancy(tenancy_factory) -> Tenancy:
    """Single tenancy fixture"""
    return tenancy_factory()[0]
