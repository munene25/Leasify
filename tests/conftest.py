import pytest
import typing
from faker import Faker
from datetime import date
from unittest.mock import MagicMock
from structlog import get_logger
from structlog.testing import capture_logs
from structlog.types import EventDict
from django.core import management as django_management, cache
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from tests.types import Factory
from common.period import DateRange
from users.models import User
from users.selectors import get_group
from users.services import user_account_create, user_set_role

from apartments.services import apartment_create
from apartments.models import Apartment
from apartments.choices import Block, Wing

from tenancy.models import Tenancy
from billing.models import BillingPeriod as BP
from billing.services import billing_period_create
from billing.choices import BillingStatus as BS

from payments.models import Payment
from payments.choices import PaymentMode as PM, PaymentStatus as PS

logger = get_logger("tests.conftest")

# ------------------------------------------------------ Globals  ------------------------------------------------------ #

# # conftest.py
# import warnings


# def pytest_configure(config):
#     warnings.filterwarnings("error", category=RuntimeWarning)


@pytest.fixture
def caplog() -> typing.Generator[list[EventDict], None, None]:
    with capture_logs() as caplog:
        yield caplog


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        django_management.call_command("loaddata", "fixtures/roles.json")


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


@pytest.fixture
def cache_clear():
    cache.cache.clear()
    yield
    cache.cache.clear()


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


@pytest.fixture(scope="session")
def fake():
    """
    Return a faker instance with a locale already set
    """

    return Faker("en_KE")


@pytest.fixture(scope="session")
def today():
    "Returns today's date"
    from django.utils import timezone

    return timezone.now().date()


# ------------------------------------------------------ Users  ------------------------------------------------------ #


@pytest.fixture(scope="session")
def user_factory(fake, phone_no) -> Factory[User]:
    """Returns a callable for generating users"""

    def create(quantity: int = 1, **kwargs: dict[str, str]) -> list[User]:
        users = []
        for _ in range(quantity):
            users.append(
                user_account_create(
                    first_name=(kwargs.get("first_name", fake.first_name())),
                    last_name=kwargs.get("last_name", fake.last_name()),
                    password="Pa55word!",
                    email=kwargs.get("email", fake.email()),
                    phone_number=kwargs.get("phone_number", phone_no()),
                    notify=False,
                )
            )
        return users

    return create


@pytest.fixture
def user(user_factory: Factory[User]) -> User:
    return user_factory()[0]


@pytest.fixture
def roles_list() -> list[Group]:
    """
    Returns a list of all available roles|Groups
    """
    return list(Group.objects.all())




@pytest.fixture
def superuser(user_factory: Factory[User]):
    u = user_factory()[0]
    u.is_superuser = True
    u.save(update_fields=["is_superuser"])
    return u


@pytest.fixture
def manager_user(user_factory: Factory[User]) -> User:
    u = user_factory()[0]
    return user_set_role(user=u, role=get_group("manager"))


@pytest.fixture
def caretaker_user(user_factory: Factory[User]) -> User:
    u = user_factory()[0]
    return user_set_role(user=u, role=get_group("caretaker"))


@pytest.fixture
def tenant_user(user_factory: Factory[User]) -> User:
    u = user_factory()[0]
    return user_set_role(user=u, role=get_group("tenant"))


@pytest.fixture(scope="session")
def password() -> str:
    """Default password for test users"""
    return "Pa55word!"


@pytest.fixture(scope="session")
def phone_no(fake) -> typing.Callable[[], str]:
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
    setattr(client, "user", user)
    return client


@pytest.fixture
def manager_client(manager_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=manager_user)
    setattr(client, "user", manager_user)
    return client


@pytest.fixture
def tenant_client(tenant_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=tenant_user)
    setattr(client, "user", tenant_user)
    return client


@pytest.fixture
def caretaker_client(caretaker_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=caretaker_user)
    setattr(client, "user", caretaker_user)
    return client


@pytest.fixture
def superuser_client(superuser) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=superuser)
    setattr(client, "user", superuser)
    return client


# ------------------------------------------------ Apartments  ------------------------------------------------


@pytest.fixture(scope="session")
def apartment_factory(fake: Faker) -> Factory[Apartment]:
    """Returns a callable for generating apartments"""
    from decimal import Decimal
    
    import random

    def create(
        quantity: int = 1, 
        unit_number: int | None = None,
        rentable: bool = True,
        floor: int | None = None,
        wing: Wing | None = None,
        rent: int | None = None,
        block: Block | None = None,
    ):
        apartments: list[Apartment] = []

        for _ in range(quantity):
            apt = Apartment.objects.create(
                block = block or random.choice(Block.values),
                floor= floor or random.choice(range(1, 6)),
                wing = wing or random.choice(Wing.values),
                unit_number = unit_number or fake.building_number(),
                rent = Decimal(rent or fake.numerify("1#000")),
                rentable = rentable
            )
            apartments.append(apt)
        return apartments

    return create


@pytest.fixture
def apartment(apartment_factory) -> Apartment:
    return apartment_factory(unit_number=1, block=Block.A, rent=20_000, rentable=True)[0]


# ------------------------------------------------ Tenancy  ------------------------------------------------
@pytest.fixture
def tenancy_patch_validators(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    user_reservations = MagicMock()
    lease_period = MagicMock()

    monkeypatch.setattr("tenancy.validators.validate_max_monthly_reservations", user_reservations)
    monkeypatch.setattr("tenancy.validators.validate_lease_period", lease_period)

    return {"user_reservations": user_reservations, "lease_period": lease_period}


@pytest.fixture(scope="session")
def tenancy_factory(apartment_factory: Factory[Apartment], user_factory: Factory[User], today: date) -> Factory[Tenancy]:
    """Tenancy generator - creates lease-based tenancies"""
    from tenancy.choices import TenancyStatus

    def create(
        quantity=1, 
        users: list[User] | None = None,
        apartments: list[Apartment] | None = None,
        start_date: date | None = None,
        status: TenancyStatus | None = None,
    ) -> list[Tenancy]:
        tenancies = []

        users = users or user_factory(quantity)
        apartments = apartments or apartment_factory(quantity=len(users), rentable=True)

        for i, user in enumerate(users):
            t = Tenancy.objects.create(
                user=user,
                apartment=apartments[i],
                date_joined=start_date or today,
                status=status or TenancyStatus.ACTIVE,
            )
            user_set_role(user=user, role=get_group("tenant"))
            tenancies.append(t)

        return tenancies

    return create


@pytest.fixture
def tenancy(tenancy_factory: Factory[Tenancy]) -> Tenancy:
    """Single tenancy fixture"""
    return tenancy_factory()[0]


# ------------------------------------------------ Mocks  ------------------------------------------------
@pytest.fixture
def mock_serializer():
    mock = MagicMock()
    mocked_instance = MagicMock()
    mocked_instance.data = {}

    mock.return_value = mocked_instance
    mock.is_valid.return_value = True
    mock.save.return_value = None
    return mock


# ------------------------------------------------ BillingPeriod  ------------------------------------------------
@pytest.fixture(scope="session")
def billing_factory(today: date, tenancy_factory: Factory[Tenancy]) -> Factory[BP]:
    def create(
        quantity=1,
        tenancy: Tenancy | None = None,
        statuses: list[BS] | None = None,
        starting: date = today,
        duration: int = 1,
    ) -> list[BP]:
        """Generate bilings for tenants"""

        tenancy = tenancy or tenancy_factory()[0]
        statuses = statuses or [BS.PAID] * quantity
        billings = []
        r = DateRange.for_month(starting)
        for s in statuses:
            b = billing_period_create(tenancy=tenancy, date_r=r)
            b.status = s
            b.save()
            billings.append(b)
            r = r.shift_months(+duration, +duration)
        return billings

    return create

@pytest.fixture()
def patch_billing_get_for(monkeypatch: pytest.MonkeyPatch, billing_factory: Factory[BP]):
    billing = billing_factory(1, statuses=[BS.UNPAID])[0]
    mock = MagicMock(return_value=billing)
    monkeypatch.setattr("billing.selectors.billing_get_for", mock)
    yield mock


# ------------------------------------------------ Payment  ------------------------------------------------
@pytest.fixture(scope="session")
def payment_factory(billing_factory: Factory[BP], phone_no: typing.Callable[..., str], fake: Faker, user_factory: Factory[User]) -> Factory[Payment]:

    def create(
        quantity=1,
        billing: BP | None = None,
        statuses: list[PS] | None = None,
        mode: PM = PM.MPESA,
        **kwargs: typing.Any,
    ) -> list[Payment]:
        """A payment creation factory, creates payments for a given billing period"""
        from payments.mpesa import make_timestamp

        billing = billing or billing_factory()[0]
        statuses = statuses or [PS.SUCCESS] * quantity
        if mode == PM.MPESA:
            kwargs.setdefault("phone_number", phone_no())
            kwargs.setdefault("receipt_no", fake.unique.uuid4())
            kwargs.setdefault("timestamp", make_timestamp())
            checkout = idemp_key = fake.unique.uuid4
        else:
            kwargs.setdefault("recorded_by", user_factory(1)[0])
            checkout = idemp_key = lambda: None
        payments = []
        for status in statuses:
            p = Payment.objects.create(
                # Required
                billing=billing,
                amount=billing.total_due,
                status=status,
                mode=mode,
                # Mpesa
                phone_number=kwargs.get("phone_number"),
                checkout_id=checkout(),
                idempotency_key=idemp_key(),
                receipt_no=kwargs.get("receipt_no"),
                timestamp=kwargs.get("timestamp"),
                # Manual
                recorded_by=kwargs.get("recorded_by"),
            )
            payments.append(p)
            logger.info(
                "payment_created",
                billing_id=p.billing_id,
                status=p.status,
                mode=p.mode,
                name=p.billing.tenancy.user.full_name,
            )
        return payments

    return create
