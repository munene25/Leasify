import random
import pytest
import typing
from faker import Faker
from django.core.management import call_command
from django.contrib.auth.models import Group
from phonenumber_field.phonenumber import PhoneNumber
from users.models import User
from users.services import user_account_create
from rest_framework.test import APIClient
from django.core.cache import cache

@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "fixtures/roles.json")


@pytest.fixture(autouse=True)
def enable_db_access(db):
    """Automatically enable db access for all tests."""
    pass

@pytest.fixture(scope="function")
def cache_clear():
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
def user_factory(fake, phone_no) -> typing.Callable[[int, dict[str, typing.Any]], list[User]]:
    """
    Returns a user object with an account created
    """

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
    return lambda name: Group.objects.get(name=name)


@pytest.fixture
def manager_user(user_factory, get_role) -> User:
    u = user_factory()[0]
    u.groups.add(get_role("manager"))
    return u


@pytest.fixture
def caretaker_user(user_factory, get_role) -> User:
    u = user_factory()[0]
    u.groups.add(get_role("caretaker"))
    return u


@pytest.fixture
def tenant_user(user_factory, get_role) -> User:
    u = user_factory()[0]
    u.groups.add(get_role("tenant"))
    return u


@pytest.fixture
def password() -> str:
    return "Pa55word!"


@pytest.fixture
def phone_no(fake) -> typing.Callable[[str | None], PhoneNumber]:
    """
    A callable to generate a phone number object
    """

    return lambda num=None: PhoneNumber.from_string(num or fake.numerify("+254-7##-###-###"))


@pytest.fixture
def client() -> APIClient:
    return APIClient()


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
def super_user_client(user) -> APIClient:
    client = APIClient()
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client.force_authenticate(user=user)
    return client
